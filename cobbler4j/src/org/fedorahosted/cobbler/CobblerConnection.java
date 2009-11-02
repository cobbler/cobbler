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

import java.net.MalformedURLException;
import java.util.Arrays;
import java.util.LinkedList;
import java.util.List;

import redstone.xmlrpc.*;

/**
 * CobblerConnection - represents an authenticatable 
 * XMLRPC connection to Cobbler.
 */

public class CobblerConnection {

    private XmlRpcClient client;
    private String token;

    /**
     * Constructor creates an authenticated connection to Cobbler.
     * read-only XMLRPC is not supported.
     * @param url  cobbler XMLRPC endpoint, ex: http://server/cobbler_api
     * @param username cobbler XMLRPC username
     * @param password cobbler XMLRPC password
     * @throws XmlRpcException on remote or communication errors
     */
    
    public CobblerConnection(String url, String user, String pass) {

        url += "/cobbler_api";

        try {
            client = new XmlRpcClient(url, false);
        }
        catch (MalformedURLException e) {
            throw new XmlRpcException(e);
        }
        token = (String) invokeNoTokenMethod("login", user, pass);
    }

    /**
     * Invoke an XMLRPC method.
     * @param method method to invoke
     * @param args args to pass to method
     * @return Object data returned.
     */
    public Object invokeNoTokenMethod(String method, List args) {
        try {
            return client.invoke(method, args);
        } 
        catch (Exception e) {
            throw new XmlRpcException("XmlRpcException calling cobbler.", e);
        } 
    }

    /**
     * Invoke an XMLRPC method.
     * @param method method to invoke
     * @param params params to pass to method
     * @return Object data returned.
     */
    public Object invokeNoTokenMethod(String method, Object ... params) {
        return invokeNoTokenMethod(method, Arrays.asList(params));
    }    


    
    /**
     * Invoke an XMLRPC method.
     * @param method method to invoke
     * @param args args to pass to method
     * @return Object data returned.
     */
    protected Object invokeMethod(String method, List params) {
        List args = new LinkedList(params);
        args.add(token);
        return invokeNoTokenMethod(method, args);
    }

    /**
     * Invoke an XMLRPC method.
     * @param method method to invoke
     * @param args args to pass to method
     * @return Object data returned.
     */
    public Object invokeMethod(String method, Object ... params) {
        return invokeMethod(method, Arrays.asList(params));
    }
    
}
