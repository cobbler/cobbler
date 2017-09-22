/**
 * Copyright (c) 2009 Red Hat, Inc.
 *
 * This software is licensed to you under the GNU General Public License,
 * version 2 (GPLv2). There is NO WARRANTY for this software, express or
 * implied, including the implied warranties of MERCHANTABILITY or FITNESS
 * FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
 * along with this software; if not, see
 * http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
 *
 * Red Hat trademarks are not licensed under GPLv2. No permission is
 * granted to use or replicate Red Hat trademarks that are incorporated
 * in this software or its documentation.
 */

package org.fedorahosted.cobbler;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.lang.reflect.Constructor;


/**
 * Base class has attributes common to
 * distros, profiles, system records
 * @author paji
 * @version $Rev$
 */
public abstract class CobblerObject {

    protected String handle;
    protected Map dataMap = new HashMap();
    protected Map blendedDataMap = new HashMap();

    protected CobblerConnection client;
    static final String NAME = "name";
    static final String UID = "uid";

    // Indicates whether or not we're an "add" or an "edit" when committed.
    protected Boolean newObject = false;

    public CobblerObject(CobblerConnection clientIn, Map dataMapIn,
            Map blendedDataMapIn) {

        client = clientIn;
        dataMap = dataMapIn;
        blendedDataMap = blendedDataMapIn;

        // If the data map we're being created with is empty, that's a very
        // strong indication this is a new object, not yet created:
        if (dataMap.keySet().size() == 0) {
            newObject = true;
        }
    }

    public abstract String getName();

    /**
     * Helper method used by all cobbler objects to
     * return a version of themselves by UID
     * @see org.cobbler.Distro.lookupById for example usage..
     *
     * @param client the Cobbler Connection
     * @param id the UID of the distro/profile/system record
     * @param findMethod the find xmlrpc method, eg: find_distro
     * @return true if the cobbler object was found.
     */

    // FIXME: generalize lookup function? "by id" seems redundant
    //protected static Map<String, Object> lookupDataMapById(CobblerConnection client, String id, String findMethod) {
    //    if (id == null) {
    //        return null;
    //    }
    //    List<Map<String, Object>> objects = lookupDataMapsByCriteria(client,
    //                                                        UID, id, findMethod);
    //    if (!objects.isEmpty()) {
    //        return objects.get(0);
    //    }
    //    return null;

    //}

    protected abstract ObjectType getObjectType();

    /**
     * look up data maps by a certain criteria
     * @param client the xmlrpc client
     * @param critera (i.e. uid profile, etc..)
     * @param value the value of the criteria
     * @param findMethod the find method to use (find_system, find_profile)
     * @return List of maps
     */

    // FIXME: refactor?
    protected static List lookupDataMapsByCriteria(
            CobblerConnection client, String critera, String value, String findMethod) {
        //if (value == null) {
        //    return null;
        //}

        //Map criteria  = new HashMap();
        //criteria.put((Object)critera, (Object)value);
        //List objects = (List) client.invokeMethod(findMethod, criteria);
        //return objects;
        return null;
    }

    /**
     * Refresh the state of this object by looking up it's data map anew from
     * the cobbler server.
     */
    private void refreshObjectState() {

        CobblerObject lookupCopy = Finder.getInstance().findItemByName(client,
                getObjectType(), getName());

        if (lookupCopy == null) {
            // This is bad, object appears to have been deleted out from underneath us
            throw new XmlRpcException("Unable to refresh object state: " + getName());
        }

        this.dataMap = lookupCopy.dataMap;
        this.blendedDataMap = lookupCopy.blendedDataMap;
    }

    protected void modify(String key, Object value) {
        // FIXME: this should modify the datamap and then have seperate 'commit'
        // semantics all in one XMLRPC command, not many with server-side state
        // representation as currently implemented
        // FIXME: invokeModify(key, value);
        dataMap.put(key, value);
    }

    protected void modify(String key, Object value, String interfaceName) {
        // FIXME: create interface hash if not already here
        HashMap interfaces = (HashMap) dataMap.get((Object)"interfaces");
        HashMap theInterface = (HashMap) interfaces.get((Object)key);
        String theName = (String) interfaces.get((Object)interfaceName);
        theInterface.put((Object)key,(Object)value);
    }

    protected Object access(String key) {
        return dataMap.get(key);
    }

    protected Object blendedAccess(String key) {
        return blendedDataMap.get(key);
    }

    protected Object access(String key, String interfaceName) {
        // FIXME: error handling
        HashMap interfaces   = (HashMap) dataMap.get((Object) "interfaces");
        HashMap theInterface = (HashMap) interfaces.get((Object)interfaceName);
        return (Object) theInterface.get((Object)key);
    }

    public String toString() {
        return getObjectType() + "\n" + dataMap.toString();
    }

    /**
     * Commit this object to the cobbler server.
     *
     * If this object is new, it will be created, otherwise an edit will be
     * performed.
     *
     * If you are creating a new object, the internal state of this object will
     * immediately be refreshed from the server. This is to accommodate the
     * defaults cobbler sets for attributes we didn't specify explicitly on our
     * object.
     */
    public void commit() {
        // Old way:
        //client.invokeMethod("commit_" + getObjectType().getName(), getHandle(),
        //        dataMap);

        if (newObject) {
            client.invokeMethod("xapi_object_edit", getObjectType().getName(),
                    getName(), "add", dataMap);
            // Now that we've been created:
            newObject = false;

            // Pickup the defaults the server set for things we didn't specify:
            refreshObjectState();
        }
        else {
            client.invokeMethod("xapi_object_edit", getObjectType().getName(),
                    getName(), "edit", dataMap);
        }

    }

    public void remove() {
        client.invokeMethod("xapi_object_edit", getObjectType().getName(),
                getName(), "remove", dataMap);
    }

    protected String getHandle() {
        if (handle == null || handle.trim().length() == 0) {
            handle = invokeGetHandle();
        }
        return handle;
    }

    private String invokeGetHandle() {
        return (String)client.invokeMethod("get_"+ getObjectType().getName() +
                "_handle", this.getName());
    }

    /**
     * Create a Cobbler object based on the given data map.
     *
     * @param type Object type. (profile, distro, system, etc)
     * @param client XMLRPC client.
     * @param dataMap Object data map. (may include "<<inherit>>" strings for some types)
     * @param blendedDataMap Blended object data map, <<inherit>>'s removed and populated
     * instead with the value from their parent objects.
     * @return
     */
    static CobblerObject load(ObjectType type, CobblerConnection client,
            Map<String, Object> dataMap, Map<String, Object> blendedDataMap) {

        try
        {
            Constructor<CobblerObject> ctor = type.getObjectClass().getConstructor(
                    new Class [] {CobblerConnection.class, Map.class, Map.class});

            CobblerObject obj = ctor.newInstance(
                    new Object [] {client, dataMap, blendedDataMap});
            return obj;
        }
        catch(Exception e) {
            throw new XmlRpcException("Class instantiation exception.", e);
        }
    }

}
