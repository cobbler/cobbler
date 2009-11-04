package org.fedorahosted.cobbler.test;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import static org.junit.Assert.*;

import org.fedorahosted.cobbler.autogen.*;
import org.fedorahosted.cobbler.*;

public class ProfileTests extends Fixture {
    
    private static final String TEST_PROFILE_NAME = "cobblertestprofile";
    private Distro testDistro;
    private Profile testProfile;
    
    public static Profile createTestProfile(Distro distro) {
        Profile newProfile = new Profile(xmlrpc);
        newProfile.setName(TEST_PROFILE_NAME);
        newProfile.setDistro(distro.getName());
        newProfile.commit();
        return newProfile;
    }
    
    @Before
    public void setUp() {
        testDistro = DistroTests.createTestDistro();
        testProfile = createTestProfile(testDistro);
    }
    
    @After
    public void tearDown() {
        try {
            testDistro.remove();
        }
        catch (XmlRpcException e) {
        }
        
        try {
            testProfile.remove();
        }
        catch (XmlRpcException e) {
        }

    }
    
    @Test 
    public void createAndDelete() {

        Profile lookedUp = (Profile)finder.findItemByName(xmlrpc, 
                ObjectType.PROFILE, testProfile.getName());
        assertEquals(lookedUp.getName(), testProfile.getName());
        
        testProfile.remove();

        lookedUp = (Profile)finder.findItemByName(xmlrpc, 
                ObjectType.PROFILE, testProfile.getName());
        assertNull(lookedUp);
    }

    @Test(expected=XmlRpcException.class)
    public void distroIsMandatory() {
        Profile profile = new Profile(xmlrpc);
        profile.setName("thisshouldfail");
        profile.commit();
    }
        
}

