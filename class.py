## Import Python modules
import sys
import visa
import time
import struct
import numpy as np
import scipy as sp
import matplotlib.pyplot as plt
import datetime
import time

##MAIN CODE
## Determine Which channels are on AND have acquired data - Scope should have already acquired data and be in a stopped state (Run/Stop button is red).
## Get Number of analog channels on scope
class Measure(object):
    def __init__(self, visa_address, timeout=10000):
        self.visa_address = visa_address
        self.timeout = timeout

    def connect(self):
        rm = visa.ResourceManager()
        try:
            self.inst = rm.open_resource(self.visa_address)
        except Exception:
            print "Unable to connect to oscilloscope at " + str(self.visa_address)

    def get_data(self):
        ### Pull waveform data, scale it
        i  = 0 # index of wave_data
        for ch in self.channels:
            if ch != 0:
                self.wave_data[:,i] = np.array(self.inst.query_binary_values(':WAVeform:SOURce CHANnel' + str(ch) + ';DATA?', "h", False))
                #print len(self.inst.query_binary_values(':WAVeform:SOURce CHANnel' + str(ch) + ';DATA?', "h", False))
                self.wave_data[:,i] = ((self.wave_data[:,i]-self.ap[ch+7])*self.ap[ch-1])+self.ap[ch+3]
                i +=1
            else:
                pass
        return self.wave_data

    def get_dataset(self,k):
        """take k dataset and get mean and std of all dataset. in the form of
        colume: time, channel1, channel2..."""
        CHS_LIST = [0,0,0,0]
        self.ap = np.zeros([12])
        ##determine datapoints and mode
        self.inst.write(":WAVeform:POINts:MODE MAX")
        DATA_POINTS = int(self.inst.query(":WAVeform:POINts?")) #number of points retrieved
        self.inst.write(":WAVeform:POINts " + str(DATA_POINTS))
    ## Find which channels are on, have acquired data, and get the pre-amble info if needed.
        ch = 1 # Channel number
        for i in CHS_LIST:
            On_Off = int(self.inst.query(":CHANnel" + str(ch) + ":DISPlay?")) # Is the channel displayed? If not, don't pull.
            if On_Off == 1: # channel is on
                Channel_Acquired = int(self.inst.query(":WAVeform:SOURce CHANnel" + str(ch) + ";POINts?"))
            else:
                Channel_Acquired = 0
            if Channel_Acquired != 0:
                CHS_LIST[ch-1] = int(ch) # in form of [1,2,0,4] if channel 1,2,4 are on
                Pre = self.inst.query(":WAVeform:PREamble?").split(',') # ## The programmer's guide has a very good description of this, under the info on :WAVeform:PREamble.
                ## In above line, the waveform source is already set; no need to reset it.
                self.ap[ch-1]  = float(Pre[7]) # Y INCrement, Voltage difference between data points; Could also be found with :WAVeform:YINCrement? after setting :WAVeform:SOURce
                self.ap[ch+3]  = float(Pre[8]) # Y ORIGin, Voltage at center screen; Could also be found with :WAVeform:YORigin? after setting :WAVeform:SOURce
                self.ap[ch+7]  = float(Pre[9]) # Y REFerence, Specifies the data point where y-origin occurs, always zero; Could also be found with :WAVeform:YREFerence? after setting :WAVeform:SOURce
            ch += 1
        self.channels = CHS_LIST
        NUM_CHS_ON = sum([1 for x in self.channels if x > 0])
        self.inst.write(":WAVeform:FORMat WORD")
        self.inst.write(":WAVeform:BYTeorder LSBFirst")
        self.inst.write(":WAVeform:UNSigned 0")
        #scale x axis and get datatime axis
        Pre = self.inst.query(":WAVeform:PREamble?").split(',')
        X_INCrement = float(Pre[4]) # Time difference between data points; Could also be found with :WAVeform:XINCrement? after setting :WAVeform:SOURce
        X_ORIGin    = float(Pre[5]) # Always the first data point in memory; Could also be found with :WAVeform:XORigin? after setting :WAVeform:SOURce
        X_REFerence = float(Pre[6]) # Specifies the data point associated with x-origin; The x-reference point is the first point displayed and XREFerence is always 0.; Could also be found with :WAVeform:XREFerence? after setting :WAVeform:SOURce
        #get data time axis
        data_time = ((np.linspace(0,DATA_POINTS-1,DATA_POINTS)-X_REFerence)*X_INCrement)+X_ORIGin
        self.time_axis = data_time
        #setting up for waveform retriving
        self.wave_data = np.zeros([DATA_POINTS,NUM_CHS_ON])
        ##calculate mean and std
        sum_data = np.zeros((DATA_POINTS,NUM_CHS_ON))
        var_data = np.zeros((DATA_POINTS,NUM_CHS_ON))
        data_list = []
        time1 = time.time()
        for i in range(k):
            indi_data = self.get_data() #indi_data is an array measured each time
            data_list.append(indi_data) #data_list is a list of individual data in array form
            sum_data += indi_data
        mean_data = sum_data / k #array
        time2 = time.time()
        print time2-time1
            #now mean_data is a array with mean of each data point after k rounds for each channel
        for each_data in data_list: #z is the individual data
            var_data += np.power(each_data - mean_data, 2)
        std_data = np.sqrt(var_data/k) #array
        mean_plus_std = np.add(mean_data,std_data)
        mean_minus_std = np.subtract(mean_data,std_data)
        z=0
        #####plot mean and standard deviation values(y) vs time(x), of all channels\
        #change channel colors
        color = ['yellow','green','blue','red']
        for ch in self.channels:
            if ch != 0:
                mean_axis = mean_data[:,z]
                plt.plot(self.time_axis,mean_axis,label = 'channel'+str(ch)+' mean',color=color[ch-1])
                mean_plus_std_axis = mean_plus_std[:,z]
                mean_minus_std_axis = mean_minus_std[:,z]
                plt.fill_between(self.time_axis,mean_plus_std_axis,mean_minus_std_axis,label = 'channel'+str(ch)+' std',linestyle='dashed',alpha=0.3,color=color[ch-1])
                z+=1
            else:
                pass
        plt.legend()
        plt.show()

    ## Save waveform data -  really, there are MANY ways to do this, of course
    def save_data_csv(self,drc=None,name='data'):
        header = "Time (s),"
        #create unit of measurement
        CH_UNITS = ["BLANK", "BLANK", "BLANK", "BLANK"]
        for channel in self.channels:
            if channel != 0:
                CH_UNITS[channel-1] = str(self.inst.query(":CHANnel" + str(channel) + ":UNITs?").strip('\n'))
        for ch in self.channels:
            if ch != 0:
                header = header + "Channel " + str(ch) + " (" + CH_UNITS[ch-1] + "),"
        ## Save data as .csv
        filename = drc + name + str(datetime.datetime.now()) + ".csv"
        with open(filename, 'w') as filehandle: # overwrite
            filehandle.write(header)
            np.savetxt(filehandle, np.insert(self.wave_data,0,self.time_axis,axis=1), delimiter=',')
                    ## Read csv data back into python with:
        with open(filename, 'r') as filehandle: # r means open for reading
            recalled_csv_data = np.loadtxt(filename,delimiter=',',skiprows=1)
        del filehandle, filename, header
        print 'CSV data has been recalled into "recalled_csv_data".\n'

    ## As a NUMPY BINARY file - fast and small, but really only good for python - can't use header
    def save_data_binary(self,drc=None,name='data'):
        filename = drc + name + str(datetime.datetime.now()) + ".npy"
        with open(filename, 'wb') as filehandle: # wb means open for writing in binary; can overwrite
            np.save(filehandle, np.insert(self.wave_data,0,self.time_axis,axis=1))
    ## Read the NUMPY BINARY data back into python with:
        with open(filename, 'rb') as filehandle: # rb means open for reading binary
            recalled_NPY_data = np.load(filehandle)
        del filename, filehandle
        print 'Binary data has been recalled into "recalled_NPY_data".\n'
