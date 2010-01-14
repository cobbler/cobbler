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

// Wildcard isn't great, but better than an explicit list of objects that
// may change.
import org.fedorahosted.cobbler.autogen.*;

public enum ObjectType {
    DISTRO ("distro", Distro.class),
    PROFILE ("profile", Profile.class),
    SYSTEM ("system", SystemRecord.class),
    IMAGE ("image", Image.class),
    REPO ("repo", Repo.class);
    private String name;
    private Class clazz;

    ObjectType (String nameIn, Class clazzIn) {
        name = nameIn;
        clazz = clazzIn;
    }

    public String getName() {
        return name;
    }

    public Class getObjectClass() {
        return clazz;
    }

    public String toString() {
        return getName();
    }
}
