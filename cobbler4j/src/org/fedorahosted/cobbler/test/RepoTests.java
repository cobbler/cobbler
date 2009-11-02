package org.fedorahosted.cobbler.test;

import java.util.List;
import org.junit.Test;
import org.junit.BeforeClass;
import static org.junit.Assert.*;

import org.fedorahosted.cobbler.autogen.*;
import org.fedorahosted.cobbler.*;

public class RepoTests extends Fixture {

    @Test 
    public void createRepo() {
        Repo newRepo = new Repo(cobblercon);
        newRepo.setName("testrepo");
        newRepo.setMirror("rsync://centos.arcticnetwork.ca/centos/5.4/os/i386/");
        newRepo.commit();

        // Now remove it:
        newRepo.remove();
        
        // TODO: Make sure it's gone...
    }

}

