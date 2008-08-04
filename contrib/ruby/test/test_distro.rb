# 
# To change this template, choose Tools | Templates
# and open the template in the editor.
 

$:.unshift File.join(File.dirname(__FILE__),'..','lib')

require 'test/unit'
require 'flexmock/test_unit'
require 'cobbler'

module Cobbler
  class TestDistro < Test::Unit::TestCase
    def setup
      @connection = flexmock('connection')
      Distro.connection = @connection
    
      @distros = Array.new
      @distros << {
        'name'           => 'Fedora-9-i386',
        'owners'         => 'admin',
        'kernel'         => '/var/www/cobbler/ks_mirror/Fedora-9-i386/images/pxeboot/vmlinuz',
        'breed'          => 'redhat',
        'depth'          => '0',
        'arch'           => 'i386',
        'initrd'         => '/var/www/cobbler/ks_mirror/Fedora-9-i386/images/pxeboot/initrd.img',
        'source_repos'   => 'http://@@http_server@@/cobbler/ks_mirror/config/Fedora-9-i386-0.repohttp://@@http_server@@/cobbler/ks_mirror/Fedora-9-i386http://@@http_server@@/cobbler/ks_mirror/config/Fedora-9-i386-1.repohttp://@@http_server@@/cobbler/ks_mirror/Fedora-9-i386',
        'kernel_options' => '',
        'parent'         => '',
        'ks_meta'        => 'treehttp://@@http_server@@/cblr/links/Fedora-9-i386'
      }
    
      @distros << {
        'name'           => 'Fedora-9-xen-i386',
        'owners'         => 'admin',
        'kernel'         => '/var/www/cobbler/ks_mirror/Fedora-9-xen-i386/images/pxeboot/vmlinuz',
        'breed'          => 'redhat',
        'depth'          => '0',
        'arch'           => 'i386',
        'initrd'         => '/var/www/cobbler/ks_mirror/Fedora-9-xen-i386/images/pxeboot/initrd.img',
        'source_repos'   => 'http://@@http_server@@/cobbler/ks_mirror/config/Fedora-9-i386-0.repohttp://@@http_server@@/cobbler/ks_mirror/Fedora-9-i386http://@@http_server@@/cobbler/ks_mirror/config/Fedora-9-i386-1.repohttp://@@http_server@@/cobbler/ks_mirror/Fedora-9-i386',
        'kernel_options' => '',
        'parent'         => '',
        'ks_meta'        => 'treehttp://@@http_server@@/cblr/links/Fedora-9-xen-i386'
      }

      @distros << {
        'name'           => 'Fedora-9-x86_64',
        'owners'         => 'admin',
        'kernel'         => '/var/www/cobbler/ks_mirror/Fedora-9-x86_64/images/pxeboot/vmlinuz',
        'breed'          => 'redhat',
        'depth'          => '0',
        'arch'           => 'x86_64',
        'initrd'         => '/var/www/cobbler/ks_mirror/Fedora-9-x86_64/images/pxeboot/initrd.img',
        'source_repos'   => 'http://@@http_server@@/cobbler/ks_mirror/config/Fedora-9-x86_64-0.repohttp://@@http_server@@/cobbler/ks_mirror/Fedora-9-i386http://@@http_server@@/cobbler/ks_mirror/config/Fedora-9-i386-1.repohttp://@@http_server@@/cobbler/ks_mirror/Fedora-9-i386',
        'kernel_options' => '',
        'parent'         => '',
        'ks_meta'        => 'treehttp://@@http_server@@/cblr/links/Fedora-9-x86_64'
      }

      @distros << {
        'name'           => 'Fedora-9-xen-x86_64',
        'owners'         => 'admin',
        'kernel'         => '/var/www/cobbler/ks_mirror/Fedora-9-xen-x86_64/images/pxeboot/vmlinuz',
        'breed'          => 'redhat',
        'depth'          => '0',
        'arch'           => 'x86_64',
        'initrd'         => '/var/www/cobbler/ks_mirror/Fedora-9-xen-x86_64/images/pxeboot/initrd.img',
        'source_repos'   => 'http://@@http_server@@/cobbler/ks_mirror/config/Fedora-9-xen-x86_64-0.repohttp://@@http_server@@/cobbler/ks_mirror/Fedora-9-i386http://@@http_server@@/cobbler/ks_mirror/config/Fedora-9-i386-1.repohttp://@@http_server@@/cobbler/ks_mirror/Fedora-9-i386',
        'kernel_options' => '',
        'parent'         => '',
        'ks_meta'        => 'treehttp://@@http_server@@/cblr/links/Fedora-9-xen-x86_64'
      }
    
    end
  
    # Ensures that finding all distros works as expected.
    #
    def test_find
      @connection.should_receive(:call).with('get_distros').once.returns(@distros)
  
      result = Distro.find
    
      assert_equal @distros.size, result.size, 'Did not get the right number of distros back'
    end
  
  end
end