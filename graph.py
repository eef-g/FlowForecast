import hydrofunctions as hf
import pandas as pd
import numpy as np

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure
from datetime import datetime, timedelta

class HydroGraph:
    """
    This is the custom class that collects, parses, and plots data from a hydro sensor
    """
    def __init__(self):
        self.ResetVariables()

    def ResetVariables(self):
        """
        Reset all class variables to allow for different sites and anchor dates to be passed through
        """
        # Self string variables
        self.sensor_id = ''
        self.anchor_date = ''
        self.sensor_name = ''
        self.current_year = ''
        self.lowest_year = ''
        self.highest_year = ''

        # Self pandas df variables
        self.sensor_df = None
        self.historic_dfs = None # <-- List of Pandas df values
        self.average_df = None
        self.lowest_df = None
        self.highest_df = None

        # Self list variables (Hold tuples for plotting data)
        self.modern_data = []
        self.lowest_data = []
        self.highest_data = []
        self.average_data = []

        # Self Matplotlib variables
        self.fig = Figure(figsize=(7,5), dpi=100)
        self.ax = self.fig.add_subplot(111) # Add a single subplot

        # Self GUI-check variable
        self.graph_finished = False
    
    def SetFullInfo(self, date, id):
        """
        Sets all of the information needed for the class at the same time
        """
        self.ResetVariables()
        self.SetSensorId(id)
        self.SetAnchorDate(date)

    def SetSensorId(self, id):
        """ Set the class's sensor_id variable to the given id"""
        self.sensor_id = id

    def SetAnchorDate(self, date):
        """ Set the class's anchor_date to the given date"""
        self.anchor_date = date
        self.current_year = date[:4]
        self.GetSensorName()
        self.CreatePlot()

    def CreatePlot(self):
        """Plot all of the data stored in the class and assign it to the Figure in the class
            [DOES NOT DISPLAY THE PLOT]"""
        # Collect all the needed data
        self.sensor_df = self.GetSensorDf(self.anchor_date, True) # Get the modern data
        self.GetHistoricDfs() # Get the historic data dfs
        self.GetHighestDf() # Get the highest flow year's df
        self.GetLowestDf() # Get the lowest flow year's df
        self.GetAverageFromData() # Create a df of the average of the historic data dfs

        # Convert the dataframes to arrays
        self.ConvertDfs() # Converts all the dfs to arrays and stores them in the class

        # Split modern x and y vals for later
        modern_x, modern_y = zip(*self.modern_data)

        # Calculate the volume & flow
        volume = self.CalculateVolume(modern_y)
        flow = self.CalculateFlow(modern_y)

        # Calculate the linear regression line -- This is our prediction for the modern data
        # Convert from 2023 timestamp to only month-day
        modern_x_timestamps = [date.timestamp() for date in self.sensor_df.index]
        slope, _ = np.polyfit(modern_x_timestamps, modern_y, 1)
        intercept = modern_y[-1] - slope * modern_x_timestamps[-1]
        linear_regression = np.poly1d([slope, intercept])
        # Plot the linear regression line starting from where the modern data left off
        regression_x = np.linspace(modern_x_timestamps[-1], (modern_x_timestamps[-1] + 604800), 67 * 7)  # Adjust the range as needed
        regression_y = linear_regression(regression_x)
        # Now convert from timestamp to dates
        regression_x = [datetime.utcfromtimestamp(date) for date in regression_x]
        temp_x = []
        for date in regression_x:
            date_str = datetime.strftime(date, '%m-%d %H:%M:%S%z')
            temp_x.append(datetime.strptime(date_str, '%m-%d %H:%M:%S'))
        regression_x = temp_x  

        # Plot the modern data
        self.ax.plot(modern_x, modern_y, color='Black', label=f'Current Year: {self.current_year}')

        # Prep and plot the highest data
        highest_x, highest_y = zip(*self.highest_data)
        self.ax.plot(highest_x, highest_y, color='Green', label=f"Highest Flow: {self.highest_year}")

        # Prep and plot the lowest data
        lowest_x, lowest_y = zip(*self.lowest_data)
        self.ax.plot(lowest_x, lowest_y, color='Blue', label=f'Lowest Flow: {self.lowest_year}')

        # Prep the average area and plot it
        avg_x, avg_y = zip(*self.average_data)
        avg_std = np.std(avg_y)
        avg_low_y = [y - avg_std for y in avg_y]
        avg_high_y = [y + avg_std for y in avg_y]

        self.ax.plot(avg_x, avg_low_y, color='Gray', linestyle='--')
        self.ax.plot(avg_x, avg_high_y, color='Gray', linestyle='--')
        self.ax.fill_between( avg_x, avg_high_y,  avg_low_y, color='Gray', alpha=0.5)

        # Plot the anchor date
        self.ax.axvline(modern_x[-1], color='r', linestyle='--', label=f'{datetime.strftime(modern_x[-1], "%b %m %H:%M")}')  # Add vertical line

        # Plot the linear regression line
        self.ax.plot(regression_x, regression_y, color='Black', linestyle='--', label="Predicted Flow")

        # Prep the plot's title & legend
        self.fig.suptitle(f'{self.sensor_name} (CFS)') # Set title of the plot
        self.ax.set_title(f'{volume:,.2f} cubic feet : dropping {flow:.2f} CFS/hr', fontsize=9)  # Set subtitle of the plot
        self.ax.xaxis.set_major_locator(mdates.DayLocator(interval=4))
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
        self.fig.autofmt_xdate()
        self.ax.legend()

        # Save the figure to disk & change the graph_finished flag for the GUI
        self.fig.savefig('plot.png')
        self.graph_finished = True


    def GetPlot(self):
        """Returns the matplotlib Figure object"""
        return self.fig


    def GetHistoricDfs(self):
        '''Returns the collection of the past 9 years from the given location over the time period'''
        overall_data = []
        for i in range(int(self.current_year) - 9, int(self.current_year)):
            today_past = str(i) + self.anchor_date[4:]
            # Request the data from year i and add it to the array
            overall_data.append(self.GetSensorDf(today_past, False))
        self.historic_dfs = overall_data # Set class variable to the array of historic dataframes


    def GetSensorDf(self, anchor, today_max=False):
        """Grabs data from the class's sensor_id variable and gets data over a 3 week period"""
        # Calculate the start date as 2 weeks in the past from today
        past_date = self.GetPastDate(anchor)
        future_date = self.GetFutureDate(anchor)

        # Check if the given anchor date is the current date
        if not today_max:
            request = hf.NWIS(self.sensor_id, 'iv', past_date, future_date, file=f'data/parquets/{self.sensor_id}-{anchor}.parquet', verbose=False)
        else:
            request = hf.NWIS(self.sensor_id, 'iv', past_date, self.anchor_date, file=f'data/parquets/{self.sensor_id}-{anchor}.parquet', verbose=False)

        # Parse the request to get the river discharge data
        discharge_df = request.df('00060')[:]
        return discharge_df


    def GetSensorName(self):
        """Uses the class's sensor_id variable to get the name of where the sensor is"""
        past_date = self.GetPastDate(self.anchor_date)
        request = hf.NWIS(self.sensor_id, 'iv', past_date, self.anchor_date, file=f'data/parquets/{self.sensor_id}-{self.anchor_date}.parquet', verbose=False)
        # From the request, parse the header and get the name of the sensor
        sensor_caps = str(request)[str(request).index(' '):str(request).index('\n')]
        sensor_title = sensor_caps.title()
        # Set the sensor name to the formatted string slices
        self.sensor_name = sensor_title[:-2] + sensor_caps[-2:]


    def GetPastDate(self, date_str):
        """Returns a string two weeks in the past from the given date"""
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        past_date = date_obj - timedelta(weeks=2)
        return past_date.strftime('%Y-%m-%d') 


    def GetFutureDate(self, date_str):
        """Returns a string one week in the future from the given date"""
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        future_date = date_obj + timedelta(weeks=1)
        return future_date.strftime('%Y-%m-%d')


    def GetLowestDf(self):
        """Finds the DataFrame that contains the lowest point from the historical data"""
        # Set lowest to the current year's lowest point
        lowest = min(self.sensor_df.loc[:, list(self.sensor_df)[0]])
        lowest_index = -1
        # Go thru each historic dataframe and look for a lower point
        for i in range(len(self.historic_dfs)):
            historic_lowest = min(self.historic_dfs[i].loc[:, list(self.historic_dfs[i])[0]])
            # If year i has a lower point than what is stored, update the stored lowest point
            if historic_lowest < lowest:
                lowest = historic_lowest
                lowest_index = i
        # Check if there was a lower point than current year's lowest & update values accordingly
        if lowest_index != -1:
            self.lowest_df = self.historic_dfs[lowest_index]
            self.lowest_year = str(int(self.current_year) - lowest_index + 1)
        else:
            self.lowest_df =  self.sensor_df
            self.lowest_year = self.current_year


    def GetHighestDf(self):
        """Finds the DataFrame that contains the highest point from the historical data"""
        # Set highest to the current year's highest point
        highest = max(self.sensor_df.loc[:, list(self.sensor_df)[0]])
        highest_index = -1
        # Go thru each historic dataframe and look for a higher point
        for i in range(len(self.historic_dfs)):
            historic_highest = max(self.historic_dfs[i].loc[:, list(self.historic_dfs[i])[0]])
            # If year i has a higher point than what is stored, update the stored highest point
            if historic_highest > highest:
                highest = historic_highest
                highest_index = i
        # Check if there was a higher point than the current year's highest & update values accordingly 
        if highest_index != -1:
            self.highest_df = self.historic_dfs[highest_index]
            self.highest_year = str(int(self.current_year) - highest_index + 1)
        else:
            self.highest_df =  self.sensor_df
            self.highest_year = self.current_year
        

    def GetAverageFromData(self):
        """Creates a dataframe that contains the average for each timestamp from all historic data"""
        # Set aside a list for where we will store the y-values
        disc_values = []
        # Go through each row of the historic dataframes
        for i in range(len(self.historic_dfs[0])):
            # Set aside list to store the current row at each historic year
            curr_time_data = []
            # Go thru each year and add the year j's value at row i
            for j in range(len(self.historic_dfs)):
                data_lump = self.historic_dfs[j].loc[:, list(self.historic_dfs[j])[0]]
                curr_time_data.append(data_lump[i])
            # Calculate the average of the row and add it to the overall average y-values
            avg = sum(curr_time_data) / len(curr_time_data)
            disc_values.append(avg)
        
        # Hijack one of the existing dataframes to keep the timestamps, but replace the column of discharge values
        output_df = self.historic_dfs[0]
        output_df.loc[:, list(output_df)[0]] = disc_values
        self.average_df = output_df


    def ConvertDfs(self):
        """Converts each class dataframe into a zipped list for graphing"""
        self.modern_data = self.DfToArray(self.sensor_df)
        self.lowest_data = self.DfToArray(self.lowest_df)
        self.highest_data = self.DfToArray(self.highest_df)
        self.average_data = self.DfToArray(self.average_df)


    def DfToArray(self, df):
        """Converts the given dataframe, df, into a zipped list"""
        columns = list(df)
        y_vals = df.loc[:, columns[0]]
        raw_dates = [str(date) for date in df.index]
        x_vals = [datetime.strptime(date[5:], '%m-%d %H:%M:%S%z') for date in raw_dates]
        return zip(x_vals, y_vals)


    def CalculateVolume(self, y_vals):
        """Calculates the river's total volume from the given y_values. Assumes that data is taken in CFS every 15 minutes."""
        # Time interval in seconds (15 minutes = 900 seconds)
        delta_t = 15 * 60
        # Calculate total volume in cubic feet
        total_volume_cubic_feet = sum(y_val * delta_t for y_val in y_vals)
        # Convert total volume to acre-feet
        total_volume_acre_feet = total_volume_cubic_feet / 43560
        return total_volume_acre_feet


    def CalculateFlow(self, y_vals):
        """Calculates the river's flow from the given y_values. Assumes that data is taken in CFS every 15 minutes."""
        if len(y_vals) < 2:
            return None
        last_val = y_vals[-1]
        for val in reversed(y_vals[:-1]):
            if val != last_val:
                change = (last_val - val) * 4  # Convert 15 minutes to hourly rate
                return abs(change)
        return 0  # Return 0 if all values are the same


if __name__ == "__main__":
    trinity_id = '11527000'
    today = '2023-06-05'
    graph = HydroGraph()
    graph.SetFullInfo(today, trinity_id)