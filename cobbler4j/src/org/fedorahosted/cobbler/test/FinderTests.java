package org.fedorahosted.cobbler.test;

import java.util.List;

import org.fedorahosted.cobbler.Config;
import org.fedorahosted.cobbler.Finder;
import org.fedorahosted.cobbler.ObjectType;
import org.fedorahosted.cobbler.autogen.Distro;
import org.fedorahosted.cobbler.autogen.Repo;
import org.junit.Before;
import org.junit.Test;

public class FinderTests extends Fixture {	

    @Test 
    public void findDistros() {
        Finder finder = Finder.getInstance();
        List<Distro> d = (List<Distro>)finder.listItems(xmlrpc, 
                ObjectType.DISTRO);
        
        for(Distro x: d){
        	System.out.println(x.getName());
        }
        // Ideally we'd check that some were returned, but we can't guarantee 
        // the cobbler server we're testing against has any distro's available.
    }

}
