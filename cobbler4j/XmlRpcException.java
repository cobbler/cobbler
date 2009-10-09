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


/**
 * @author paji
 * @version $Rev$
 */
public class XmlRpcException extends RuntimeException {
    /**
     * 
     */
    private static final long serialVersionUID = 1L;

    /**
     * @param messageIn exception message
     */
    public XmlRpcException(String messageIn) {
        super(messageIn);
    }

    /**
     * @param causeIn cause
     */
    public XmlRpcException(Throwable causeIn) {
        super(causeIn);
    }    
    
    /**
     * @param messageIn exception message
     * @param causeIn cause
     */
    public XmlRpcException(String messageIn, Throwable causeIn) {
        super(messageIn, causeIn);
    }

}
