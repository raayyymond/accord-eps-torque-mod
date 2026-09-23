import sys, os, boot
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "pylibs"))
boot.setup()
import pytest
args = sys.argv[1:]
sys.exit(pytest.main(["-p", "no:cacheprovider", "--noconftest", "-q", "-o", "addopts=", "--rootdir", str(boot.ROOT)] + args))
