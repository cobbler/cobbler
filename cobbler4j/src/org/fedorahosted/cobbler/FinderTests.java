package org.fedorahosted.cobbler;

import java.util.List;
import org.junit.Test;
import org.junit.BeforeClass;
import static org.junit.Assert.*;

import org.fedorahosted.cobbler.autogen.*;

public class FinderTests {

    public static final String user = "testing";
    public static final String pass = "testing";
    public static CobblerConnection cobblercon;

    @BeforeClass 
    public static void establishConnection() {
        cobblercon = new CobblerConnection("http://192.168.1.1",
                user, pass);
    }

    @Test 
    public void findSomething() {
        Finder finder = Finder.getInstance();
        // TODO: Will fail if your cobbler server has no distros:
        List<Distro> d = (List<Distro>)finder.listItems(cobblercon, 
                ObjectType.DISTRO);

        // Ideally we'd check that some were returned, but we can't guarantee 
        // the cobbler server we're testing against has any distro's available.
    }

}
