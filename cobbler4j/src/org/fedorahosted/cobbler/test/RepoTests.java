package org.fedorahosted.cobbler.test;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import static org.junit.Assert.*;

import org.fedorahosted.cobbler.autogen.*;
import org.fedorahosted.cobbler.*;

public class RepoTests extends Fixture {
    
    private static final String TEST_REPO_NAME = "testrepo";
    private Repo testRepo;
    
    @Before
    public void setUp() {
        // Create a test repo we can operate on in this suite:
        testRepo = new Repo(xmlrpc);
        testRepo.setName(TEST_REPO_NAME);
        testRepo.setMirror("rsync://centos.arcticnetwork.ca/centos/5.4/os/i386/");
        testRepo.commit();
    }
    
    @After
    public void tearDown() {
        // Now remove it:
        try {
            testRepo.remove();
        }
        catch (XmlRpcException e) {
            // tis' ok, the test probably deleted it already
        }
    }

    @Test 
    public void createAndDeleteRepo() {

        Repo lookedUp = (Repo)finder.findItemByName(xmlrpc, 
                ObjectType.REPO, TEST_REPO_NAME);
        assertEquals(lookedUp.getName(), TEST_REPO_NAME);
        
        testRepo.remove();

        lookedUp = (Repo)finder.findItemByName(xmlrpc, 
                ObjectType.REPO, TEST_REPO_NAME);
        assertNull(lookedUp);
    }

    // TODO: Checking for a pretty generic exception here, NoSuchBlah exception would 
    // be nice.
    @Test(expected = XmlRpcException.class)
    public void deleteNoSuchRepo() {
        Repo newRepo = new Repo(xmlrpc);
        newRepo.setName("nosuchrepo");
        newRepo.remove();
    }
    
    @Test 
    public void testEditRepo() {
        testRepo.setKeepUpdated(false);
        testRepo.commit();
        Repo lookedUp = (Repo)finder.findItemByName(xmlrpc, 
                ObjectType.REPO, TEST_REPO_NAME);
        assertFalse(lookedUp.getKeepUpdated());
        
        testRepo.setKeepUpdated(true);
        testRepo.commit();
        
        lookedUp = (Repo)finder.findItemByName(xmlrpc, 
                ObjectType.REPO, TEST_REPO_NAME);
        assertTrue(lookedUp.getKeepUpdated());
    }
}

