# Sunspot: ephemeris engine for automated telescope guidance

class Ephemeris:
    RAW_DATA = None
    def __init__(self, start_time:str, stop_time:str, observer_location:str, step_size:str, target_body:str ):
        self.RAW_DATA = get_jpl_ephemeris( start_time, stop_time, observer_location, step_size, target_body )
    def get_ephemeris_data_column_headers(self):
        """
        :return: A list of data column headers.
        """
        pass
    def get_cleaned_ephemeris_data(self):
        """
        :return: A monolithic string of ephemeris data, omitting header and footer.
        """
        pass
    def get_ephemeris_data( self, column_header ):
        """
        :param column_header: String header corresponding to a column of ephemeris data, e.g., "Date__(UT)__HR:MN"
        :return: A list of data corresponding to an ephemeris data column header.
        """
        pass
    def get_corresponding_data(self, target_data_column_header, source_data_column_header, source_data_point ):
        """
        Retrieve data point from within target_data_column, corresponding to source_data_point from within source_data_column.
        :param target_data_column_header: String header corresponding to a column of ephemeris data in which to search, e.g., "Date__(UT)__HR:MN"
        :param source_data_column_header: String header corresponding to a column of ephemeris data from where search datum originates, e.g., "Date__(UT)__HR:MN"
        :param source_data_point: String datum found within source_data_column for which a corresponding row returns.
        :return: Datum from row of target_data_column, from where source_data_point is found in source_data_column
        """
        pass
    def help(self):
        print( "For details about the NASA/JPL Horizons API, see: https://ssd.jpl.nasa.gov/horizons/manual.html#center .\n,"
               "The NASA/JPL Horizons Ephemeris service is not affiliated with the sunspot.py API.")

class Tracker:
    def __init__(self, e):
        pass

def get_jpl_ephemeris(  start_time,  # 'YYYY-MM-DD'
                        stop_time,  # 'YYYY-MM-DD'
                        observer_location,  # 'LA,LO,EL'
                        step_size,  # e.g., "1 d"
                        target_body, # E.g. 'Sol' is the sun. Search target_bodies here: https://ssd.jpl.nasa.gov/horizons/app.html#/
                        center='coord@399'  # relates to target location on object
                        ):
    import urllib.request
    url = [
        "https://ssd.jpl.nasa.gov/api/horizons.api?format=text&MAKE_EPHEM='YES'&EPHEM_TYPE='OBSERVER'&COORD_TYPE='GEODETIC'&CENTER='coord@399'&QUANTITIES='2,4'&REF_SYSTEM='ICRF'&CAL_FORMAT='CAL'&CAL_TYPE='M'&TIME_DIGITS='MINUTES'&ANG_FORMAT='HMS'&APPARENT='AIRLESS'&RANGE_UNITS='AU'&SUPPRESS_RANGE_RATE='NO'&SKIP_DAYLT='NO'&SOLAR_ELONG='0,180'&EXTRA_PREC='NO'&R_T_S_ONLY='NO'&CSV_FORMAT='NO'&OBJ_DATA='YES'&",
        "COMMAND=" + "'" + target_body + "'" + "&",
        "SITE_COORD=" + "'" + observer_location + "'" + "&",
        "START_TIME=" + "'" + start_time + "'" + "&",
        "STOP_TIME=" + "'" + stop_time + "'" + "&",
        "STEP_SIZE=" + "'" + step_size + "'"]
    url = ''.join(url)
    # TODO url = url.replace( "=", "%3D" )
    # TODO url = url.replace( ";", "%3B" )
    url = url.replace(" ", "%20")
    response = urllib.request.urlopen( url )
    # print( url )
    response = response.read().decode('UTF-8')
    g = validate_ephemeris_data( response )
    print( g)
    return response

def validate_ephemeris_data( response ):
    """
    Identify and intercept common errors before returning ephemeris string to user.
    :param response: String of text returning from NASA/JPL Horizons API query
    :return: None if response contains no errors. Else, exception raised and execution stops.
    """
    p = "NASA/JPL Horizons API detects fault: "
    if "Cannot use print-out interval <= zero" in response:
        raise SystemError( p + "'Cannot use print-out interval <= zero'. Confirm valid temporal step size." )
    if "Bad dates -- start must be earlier than stop" in response:
        raise SystemError( p + "'Bad dates -- start must be earlier than stop'. Check start or stop time." )
    if "Cannot interpret date. Type \"?!\" or try YYYY-MMM-DD {HH:MN} format" in response:
        raise SystemError( p + "'Cannot interpret date. Type \"?!\" or try YYYY-MMM-DD {HH:MN} format'. Check date format." )
    if "Cannot interpret date. Type \"?!\" or try YYYY-Mon-Dy {HH:MM} format." in response:
        raise SystemError( p + "Cannot interpret date. Type \"?!\" or try YYYY-Mon-Dy {HH:MM} format.'. Check date format." )
    if "No matches found." in response:
        raise SystemError( p + "'No matches found.' Verify matching 'Target Body' here: https://ssd.jpl.nasa.gov/horizons/app.html#/" )
    if "Use ID# to make unique selection" in response:
        raise SystemError( p + "'Use ID# to make unique selection'. Use precise ID# to narrow 'Target Body' search: https://ssd.jpl.nasa.gov/horizons/app.html#/" )
    if "No site matches. Use \"*@body\" to list, \"c@body\" to enter coords, ?! for help." in response:
        raise SystemError( p + "'No site matches. Use \"*@body\" to list, \"c@body\" to enter coords, ?! for help.'. Check 'Target Body' center." )
    if "Observer table for observer=target disallowed." in response:
        raise SystemError( p + "'Observer table for observer=target disallowed.' Cannot view Earth from Earth." )
    if "Unknown units specification -- re-enter" in response:
        raise SystemError( p + "'Unknown units specification -- re-enter'. Check Step_Size argument format." )
    if "exceeds 90024 line max -- change step-size" in response:
        raise SystemError( p + "'Projected output length... exceeds 90024 line max -- change step-size'. Horizons prints a 90024 row maximum." )