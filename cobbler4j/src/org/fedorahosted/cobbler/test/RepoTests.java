package org.fedorahosted.cobbler.test;

import org.junit.Test;
import static org.junit.Assert.*;

import org.fedorahosted.cobbler.autogen.*;
import org.fedorahosted.cobbler.*;

public class RepoTests extends Fixture {

    @Test 
    public void createRepo() {

        String repoToCreate = "testrepo";

        Repo newRepo = new Repo(cobblercon);
        newRepo.setName(repoToCreate);
        newRepo.setMirror("rsync://centos.arcticnetwork.ca/centos/5.4/os/i386/");
        newRepo.commit();

        Repo lookedUp = (Repo)finder.findItemByName(cobblercon, 
                ObjectType.REPO, repoToCreate);
        assertEquals(lookedUp.getName(), repoToCreate);

        // Now remove it:
        newRepo.remove();

        lookedUp = (Repo)finder.findItemByName(cobblercon, 
                ObjectType.REPO, repoToCreate);
        assertNull(lookedUp);
    }

}

