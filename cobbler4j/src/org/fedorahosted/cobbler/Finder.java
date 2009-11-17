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

import java.util.List;
import java.util.LinkedList;
import java.util.Map;
import java.util.HashMap;

public class Finder {
    private static final Finder INSTANCE = new Finder();

    private Finder() { 
    }

    public static Finder getInstance() {
        return INSTANCE;
    }

    @SuppressWarnings("unchecked")
    public List<? extends CobblerObject> findItems(CobblerConnection client,
            ObjectType type, String critera, String value) {
        
        if (value == null) {
            return null;
        }

        Map<String, String> criteria  = new HashMap<String, String>();
        criteria.put(critera, value);

        List<Map<String, Object>> objects = (List<Map<String, Object>>)
            client.invokeMethod("find_" + type.getName(), criteria);
        return maps2Objects(client, type, objects);
    }

    private List <? extends CobblerObject> maps2Objects(CobblerConnection client,
            ObjectType type, List<Map<String, Object>> maps) {
        
        List<CobblerObject> ret = new LinkedList<CobblerObject>();
        for (Map<String, Object> obj : maps) {

            // If we're looking for a system or a profile, call a different XMLRPC,
            // method to get "blended" data. These objects in cobbler have a crude
            // inheritence method where by child objects specify the field set as
            // "<<inherit>>", indicating the value for this setting has to come
            // from the parent object. Blending is Cobbler's process by which these
            // fields get set. Profiles and systems are the only two objects supporting
            // this blending.
            
            // This does result in two calls but I think it's the only way to get this
            // right...
            
            // Will remain null except for profiles and systems:
            Map<String, Object> blendedDataMap = null;
            if (type == ObjectType.PROFILE) {
               blendedDataMap = (Map<String, Object>)
                    client.invokeMethod("get_blended_data", obj.get("name"));
            }
            else if (type == ObjectType.SYSTEM) {
                // TODO: need a test for this
                blendedDataMap = (Map<String, Object>)
                    client.invokeMethod("get_blended_data", "", obj.get("name"));
            }
            
            ret.add(CobblerObject.load(type, client, obj, blendedDataMap));
        }
        
        return ret;
    }

    public CobblerObject findItemById(CobblerConnection client,
            ObjectType type, 
            String id) {
        if (id == null) {
            return null;
        }
        List <? extends CobblerObject> items = findItems(client, type, 
                CobblerObject.UID, id);
        if (items.isEmpty()) {
            return null;
        }
        return items.get(0);
    }

    public CobblerObject findItemByName(CobblerConnection client,
            ObjectType type, String name) {
        if (name == null) {
            return null;
        }

        List <? extends CobblerObject> items = findItems(client, type, 
                CobblerObject.NAME, name);
        if (items.isEmpty()) {
            return null;
        }
        return items.get(0);
    }

    @SuppressWarnings("unchecked")
    public List<? extends CobblerObject> listItems(CobblerConnection client, 
            ObjectType type) {
        List<Map<String, Object>> objects = (List<Map<String, Object>>)
            client.invokeNoTokenMethod("get_" + type.getName()+ "s");
        return maps2Objects(client, type, objects);
    }
}
