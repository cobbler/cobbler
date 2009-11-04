package org.fedorahosted.cobbler.test;

import org.fedorahosted.cobbler.CobblerConnection;
import org.fedorahosted.cobbler.Config;
import org.fedorahosted.cobbler.Finder;
import org.fedorahosted.cobbler.PropertyLoader;
import org.junit.BeforeClass;

public class Fixture {

    public static CobblerConnection xmlrpc;
    public static Finder finder;

    @BeforeClass 
    public static void establishConnection() {
    	// Config myConfig = new Config();
		 PropertyLoader p = new PropertyLoader();
	     try {
			p.load();
		} catch (Exception e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
    	
    	
        xmlrpc = new CobblerConnection(Config.getHostname(),
        		Config.getUser(), Config.getPassword());
        finder = Finder.getInstance();
      
    }

}

