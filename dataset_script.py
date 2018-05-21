#script: test.py k
import sys
import osclass2
scope = osclass2.Measure('USB0::2391::6040::MY50512036::INSTR')
scope.connect()
scope.get_dataset(int(sys.argv[1]))
