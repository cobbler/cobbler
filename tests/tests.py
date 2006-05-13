import sys
import unittest
import traceback

from koan import koan

class Basic(unittest.TestCase):
    """
    Koan is very network, system, and configuration dependent, so there isn't
    a *ton* of things that can be added here.  But things *should* be added.
    """
    def setUp(self):
       pass

    def tearDown(self):
       pass

    def test_basicCli(self):
       try:
           koan.main()
       except SystemExit:
           pass
       except:
           traceback.print_exc()
           self.fail("raised exception")
       
if __name__ == "__main__":
    unittest.main(argv=sys.argv)
