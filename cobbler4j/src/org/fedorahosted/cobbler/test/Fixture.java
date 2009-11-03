package org.fedorahosted.cobbler.test;

import org.junit.BeforeClass;

import org.fedorahosted.cobbler.*;

public class Fixture {

    // TODO: Get these from some kind of user defined test config file:
    public static final String user = "testing";
    public static final String pass = "testing";
    public static CobblerConnection cobblercon;
    public static Finder finder;

    @BeforeClass 
    public static void establishConnection() {
        cobblercon = new CobblerConnection("http://192.168.1.1",
                user, pass);
        finder = Finder.getInstance();
    }

}

