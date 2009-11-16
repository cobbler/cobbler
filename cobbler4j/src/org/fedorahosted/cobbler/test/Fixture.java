package org.fedorahosted.cobbler.test;

import org.fedorahosted.cobbler.CobblerConnection;
import org.fedorahosted.cobbler.Finder;
import org.fedorahosted.cobbler.PropertyLoader;
import org.junit.BeforeClass;

public class Fixture {

    public static CobblerConnection xmlrpc;
    public static Finder finder;

    @BeforeClass
    public static void establishConnection() {

        // TODO: This is tricky, we're actually setting system propoerties by creating this
        // property loader. It's likely something that should get moved to a 
        // static block in some test subpackage code.
        PropertyLoader p = new PropertyLoader();
        try {
            p.load();
        } catch (Exception e) {
            // TODO Auto-generated catch block
            e.printStackTrace();
        }

        xmlrpc = new CobblerConnection(Config.getHostname(), Config.getUser(),
                Config.getPassword());
        finder = Finder.getInstance();

    }

}

