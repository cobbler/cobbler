package org.fedorahosted.cobbler.test;

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
//    
//    @Test 
//    public void testEditRepo() {
//        testRepo.setKeepUpdated(false);
//        testRepo.commit();
//        Repo lookedUp = (Repo)finder.findItemByName(xmlrpc, 
//                ObjectType.REPO, TEST_REPO_NAME);
//        assertFalse(lookedUp.getKeepUpdated());
//        
//        testRepo.setKeepUpdated(true);
//        testRepo.commit();
//        
//        lookedUp = (Repo)finder.findItemByName(xmlrpc, 
//                ObjectType.REPO, TEST_REPO_NAME);
//        assertTrue(lookedUp.getKeepUpdated());
//    }
//    
//    @Test
//    public void testUnsetParamsOnNewRepo() {
//        Repo lookedUp = (Repo)finder.findItemByName(xmlrpc, 
//                ObjectType.REPO, TEST_REPO_NAME);
//        assertNotNull(testRepo.getPriority());
//        assertEquals(testRepo.getPriority(), lookedUp.getPriority());
//    }
//    
//    @Test 
//    public void testBigEdit() {
//        String arch = "x86_64";
//        String comment = "hello world!";
//        
//        testRepo.setArch(arch);
//        testRepo.setComment(comment);
//        testRepo.setMirrorLocally(false);
//        testRepo.commit();
//        
//        assertEquals(arch, testRepo.getArch());
//        assertEquals(comment, testRepo.getComment());
//        assertFalse(testRepo.getMirrorLocally());
//        
//        Repo lookedUp = (Repo)finder.findItemByName(xmlrpc, 
//                ObjectType.REPO, TEST_REPO_NAME);
//        
//        assertEquals(testRepo.getArch(), lookedUp.getArch());
//        assertEquals(testRepo.getComment(), lookedUp.getComment());
//        assertFalse(lookedUp.getMirrorLocally());
//        
//    }
}

