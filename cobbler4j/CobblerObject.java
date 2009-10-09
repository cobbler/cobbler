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

import java.util.Arrays;
import java.util.Collection;
import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;


/**
 * Base class has attributes common to 
 * distros, profiles, system records
 * @author paji
 * @version $Rev$
 */
public abstract class CobblerObject {
    
    protected String handle;
    protected Map<String, Object> dataMap = new HashMap<String, Object>();
    protected CobblerConnection client;    

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
    protected static Map<String, Object> lookupDataMapById(CobblerConnection client, 
                             String id, String findMethod) {
        if (id == null) {
            return null;
        }
        List<Map<String, Object>> objects = lookupDataMapsByCriteria(client,
                                                            UID, id, findMethod);
        if (!objects.isEmpty()) {
            return objects.get(0);
        }
        return null;

    }

    /**
     * look up data maps by a certain criteria
     * @param client the xmlrpc client
     * @param critera (i.e. uid profile, etc..)
     * @param value the value of the criteria
     * @param findMethod the find method to use (find_system, find_profile)
     * @return List of maps
     */

    // FIXME: refactor?
    protected static List<Map<String, Object>> lookupDataMapsByCriteria(
            CobblerConnection client, String critera, String value, String findMethod) {
        if (value == null) {
            return null;
        }

        Map<String, String> criteria  = new HashMap<String, String>();
        criteria.put(critera, value);
        List<Map<String, Object>> objects = (List<Map<String, Object>>)
                                client.invokeTokenMethod(findMethod, criteria);
        return objects;

    }
    

    /**
     * Helper method used by all cobbler objects to 
     * return a Map of themselves by name.
     * @see org.cobbler.Distro.lookupByName for example usage..
     * @param client  the Cobbler Connection
     * @param name the name of the cobbler object
     * @param lookupMethod the name of the xmlrpc
     *                       method to lookup: eg get_profile for profile 
     * @return the Cobbler Object Data Map or null
     */

    // FIXME: refactor?
    //protected static Map <String, Object> lookupDataMapByName(CobblerConnection client, 
    //                                String name, String lookupMethod) {
    //    Map <String, Object> map = (Map<String, Object>)client.
    //                                    invokeMethod(lookupMethod, name);
    //    if (map == null || map.isEmpty()) {
    //        return null;
    //    }
    //    return map;
    //}
    
    protected void modify(String key, Object value) {
        // FIXME: this should modify the datamap and then have seperate 'commit'
        // semantics all in one XMLRPC command, not many with server-side state
        // representation as currently implemented
        // FIXME: invokeModify(key, value);
        dataMap.put(key, value);
    }
    
    protected void modify(String key, Object value, String interfaceName) {
        // FIXME: create interface hash if not already here
        HashMap<String, Object> interfaces = dataMap.get(key, "interfaces");
        HashMap<String, Object> theInterface = interfaces.get(key, interfaceName);
        theInterface.put(key,value);
    }
   
    protected Object access(String key) {
        return dataMap.get(key);
    }
 
    protected void access(String key, String interfaceName) {
        HashMap<String, Object> interfaces   = dataMap.get(key, "interfaces");
        HashMap<String, Object> theInterface = interfaces.get(key, interfaceName);
        return theInterface.get(key);
    }
   
    public String toString() {
        return getObjectType() + dataMap.toString();
    }

}
