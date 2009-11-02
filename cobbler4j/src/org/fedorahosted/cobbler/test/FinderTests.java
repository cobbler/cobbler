package org.fedorahosted.cobbler.test;

import java.util.List;
import org.junit.Test;
import org.junit.BeforeClass;
import static org.junit.Assert.*;

import org.fedorahosted.cobbler.autogen.*;
import org.fedorahosted.cobbler.*;

public class FinderTests extends Fixture {

    @Test 
    public void findDistros() {
        Finder finder = Finder.getInstance();
        List<Distro> d = (List<Distro>)finder.listItems(cobblercon, 
                ObjectType.DISTRO);

        // Ideally we'd check that some were returned, but we can't guarantee 
        // the cobbler server we're testing against has any distro's available.
    }

}
