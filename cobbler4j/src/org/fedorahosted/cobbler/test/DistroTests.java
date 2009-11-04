package org.fedorahosted.cobbler.test;

import java.util.LinkedList;
import java.util.List;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import static org.junit.Assert.*;

import org.fedorahosted.cobbler.autogen.*;
import org.fedorahosted.cobbler.*;

public class DistroTests extends Fixture {
    
    private static final String TEST_DISTRO_NAME = "cobblertestrepo";
    private Distro testDistro;
    
    @Before
    public void setUp() {
        testDistro = new Distro(xmlrpc);
        testDistro.setName(TEST_DISTRO_NAME);
        // FIXME: This is super gross, but we need a test distro, and cobbler doesn't
        // seem to care if you pass it rubbish for the kernel/initrd.
        testDistro.setKernel("/etc/hosts");
        testDistro.setInitrd("/etc/hosts");
        testDistro.commit();
    }
    
    @After
    public void tearDown() {
        // Now remove it:
        try {
            testDistro.remove();
        }
        catch (XmlRpcException e) {
            // tis' ok, the test probably deleted it already
        }
    }
    
    @Test 
    public void createAndDelete() {

        Distro lookedUp = (Distro)finder.findItemByName(xmlrpc, 
                ObjectType.DISTRO, TEST_DISTRO_NAME);
        assertEquals(lookedUp.getName(), TEST_DISTRO_NAME);
        
        testDistro.remove();

        lookedUp = (Distro)finder.findItemByName(xmlrpc, 
                ObjectType.DISTRO, TEST_DISTRO_NAME);
        assertNull(lookedUp);
    }

    @Test(expected=XmlRpcException.class)
    public void kernelIsMandatory() {
        testDistro = new Distro(xmlrpc);
        testDistro.setName(TEST_DISTRO_NAME);
        testDistro.setInitrd("/etc/hosts");
        testDistro.commit();
    }
    
    @Test(expected=XmlRpcException.class)
    public void initrdIsMandatory() {
        testDistro = new Distro(xmlrpc);
        testDistro.setName(TEST_DISTRO_NAME);
        testDistro.setKernel("/etc/hosts");
        testDistro.commit();
    }
    
    // TODO: Checking for a pretty generic exception here, NoSuchBlah exception would 
    // be nice.
    @Test(expected = XmlRpcException.class)
    public void deleteNoSuchDistro() {
        Distro newDistro = new Distro(xmlrpc);
        newDistro.setName("nosuchrepo");
        newDistro.remove();
    }
    
    @Test(expected=XmlRpcException.class)
    public void setInvalidOsVersion() {
        testDistro.setOsVersion("alskdhals");
        testDistro.commit();
    }
    
    @Test 
    public void testEditDistro() {
        testDistro.setOsVersion("generic26");
        List<String> owners = new LinkedList<String>();
        owners.add("admin");
        owners.add("testing");
        owners.add("somebodyelse");
        testDistro.setOwners(owners);
        testDistro.commit();
        
        Distro lookedUp = (Distro)finder.findItemByName(xmlrpc, 
                ObjectType.DISTRO, TEST_DISTRO_NAME);
        assertEquals("generic26", lookedUp.getOsVersion());
        assertEquals(3, lookedUp.getOwners().size());
    }
    
}

