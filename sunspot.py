"""
Sunspot: Simple and light-weight ephemeris engine for automated telescope guidance and astronomical observation.

Powered by NASA/JPL Horizons Ephemeris API, which is not affiliated with Sunspot.
For NASA/JPL information, see: https://ssd.jpl.nasa.gov/horizons/manual.html#center

__author__ = "Phillip Curtsmith"
__copyright__ = "Copyright 2023, Phillip Curtsmith"

__license__ = "MIT"
__version__ = "1.0.1"
__maintainer__ = "Phillip Curtsmith"
__email__ = "phillip.curtsmith@gmail.com"
"""

DATA_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_EPHEMERIS_QUANTITIES = '1,2,4'
SOLAR_AND_LUNAR_PRESENCE_SYMBOLS = [ 'C', 'm', 'N', 'A', '*', '' ]
VALID_STEP_LABELS = [ 'minute', 'hour', 'day', 'month', 'year' ]


class Ephemeris:

    def __init__( self, start_time: str, stop_time: str, observer_location: str, step_size: str, target_body: str, quantities: str = DEFAULT_EPHEMERIS_QUANTITIES ):
        """
        :param start_time: 'YYYY-MM-DD HH:MM:SS'
        :param stop_time: 'YYYY-MM-DD HH:MM:SS'
        :param observer_location: '00,00,00' as 'latitude [fractional degrees], longitude [fractional degrees], elevation [kilometers]'
        :param step_size: 'n t', where 1 <= n <= 90024 (the maximum number of entries) and t is a unit of time, e.g., 'minute', 'hour', 'day', 'month', 'year'
        :param target_body: observable target from JPL index, here: https://ssd.jpl.nasa.gov/horizons/app.html#/
        """
        self.RAW_DATA = get_jpl_ephemeris( start_time, stop_time, observer_location, step_size, target_body, quantities )
        self.DATA_ENTRIES_RAW, self.DATA_ENTRIES, self.DATA_TITLES = self.clean_ephemeris_data()
        self.PARSED_DATA = self.parse_ephemeris_data()

    def clean_ephemeris_data( self ) -> list:
        """
        :return: A list of strings of ephemeris data, where each list entry is a row of data for a given time. Omits header and footer.
        """
        data_entries_raw = self.RAW_DATA.split( "\n" )
        data_titles = data_entries_raw[ data_entries_raw.index("$$SOE") - 2 ].split( ',' )
        data_titles = [ i.strip(' ') for i in data_titles ]
        data_titles = [ i for i in data_titles if i != '' ]
        data_entries = data_entries_raw[ data_entries_raw.index("$$SOE") + 1 : data_entries_raw.index("$$EOE") ]
        return data_entries_raw, data_entries, data_titles

    def parse_ephemeris_data( self ) -> dict:
        """
        :return: A dictionary of ephemeris data, where keys are data column titles and each value is a list of data corresponding to that title. Entries in each list are in chronological order.
        """
        from collections import defaultdict
        ephemeris = defaultdict( list )
        for row in self.DATA_ENTRIES:
            row_items = row.split( ',' )
            row_items = [ i.strip(' ') for i in row_items ]
            row_items = [ i for i in row_items if i not in SOLAR_AND_LUNAR_PRESENCE_SYMBOLS ]
            for column in range( len(self.DATA_TITLES) ):
                ephemeris[ self.DATA_TITLES[column] ].append( row_items[column] )
        return ephemeris

    def get_ephemeris_data( self, column_title: str ) -> list:
        """
        :param column_title: String title corresponding to a column of ephemeris data, e.g., "Date__(UT)__HR:MN:SS"
        :return: A list of data corresponding to an ephemeris data column title. Entries in this list are in chronological order.
        """
        if not self.DATA_TITLES.__contains__( column_title ):
            raise SystemError( "'" + column_title + "'" + " is not a valid ephemeris data column title." )
        return self.PARSED_DATA.get( column_title )

    def dates( self ) -> list:
        """
        :return: A list of ephemeris dates, in chronological order.
        """
        return self.get_ephemeris_data( self.DATA_TITLES[0] )

    def find_corresponding_data( self, target_data_column_title: str, source_data_column_title: str, source_data_point: str ):
        """
        Retrieve data point from within target_data_column, corresponding to source_data_point from within source_data_column.
        :param target_data_column_title: String title corresponding to a column of ephemeris data in which to search, e.g., "Azi____(a-app)___Elev"
        :param source_data_column_title: String title corresponding to a column of ephemeris data from where search datum originates, e.g., "Date__(UT)__HR:MN:SS"
        :param source_data_point: String datum found within source_data_column for which a corresponding row returns.
        :return: None if source_data_point not found in source_data. If source_data_point appears only once, return corresponding datum from target_data. If source_data_point appears more than once, return a list of corresponding data in chronological order.
        """
        source_data = self.get_ephemeris_data( source_data_column_title )
        if not source_data.__contains__( source_data_point ):
            return None
        target_data = self.get_ephemeris_data( target_data_column_title )
        if source_data.count( source_data_point ) == 1:
            return target_data[ source_data.index( source_data_point ) ]
        h = []
        for i in range( len(target_data) ):
            if source_data[i] == source_data_point:
                h.append( target_data[i] )
        return h


class Tracker:
    """
    Create Tracker object
        - Constructor arguments:
            - Ephemeris object
            - Ephemeris column label(s) for tracking
            - User local method to invoke
        - Method to kill Tracker
    """
    def __init__( self, e: Ephemeris ):
        pass


def convert_numeric_month( r ) -> str:
    return r.replace( "Jan", "01" ).replace( "Feb", "02" ).replace( "Mar", "03" ).replace( "Apr", "04" ).replace( "May", "05" ).replace( "Jun", "06" ).replace( "Jul", "07" ).replace( "Aug", "08" ).replace( "Sep", "09" ).replace( "Oct", "10" ).replace( "Nov", "11" ).replace( "Dec", "12" )


def get_jpl_ephemeris(  start_time: str,
                        stop_time: str,
                        observer_location: str,
                        step_size: str,
                        target_body: str,
                        quantities = DEFAULT_EPHEMERIS_QUANTITIES ) -> str:
    """
    :param start_time: 'YYYY-MM-DD HH:MM:SS' Note: 24h clock. See: https://ssd.jpl.nasa.gov/tools/jdc/#/cd
    :param stop_time: 'YYYY-MM-DD HH:MM:SS'
    :param observer_location: '00,00,00' as 'longitude [fractional degrees, positive is east of prime meridian], latitude [fractional degrees, positive is north of equator], elevation [kilometers]'
    :param step_size: 'n t', where 1 <= n <= 90024 and t is a unit of time, e.g., 'minute', 'hour', 'day', 'month', 'year'
    :param target_body: observable target from JPL index, here: https://ssd.jpl.nasa.gov/horizons/app.html#/
    :param quantities: comma-delimited string of integers corresponding to data available from JPL. "Edit Table Settings" for a complete list, here: https://ssd.jpl.nasa.gov/horizons/app.html#/
    :return String of data from NASA/JPL Ephemeris service.
    """
    import urllib.request
    validate_jpl_ephemeris_date( start_time )
    validate_jpl_ephemeris_date( stop_time )
    validate_jpl_ephemeris_step_unit( step_size )
    url = [
        "https://ssd.jpl.nasa.gov/api/horizons.api?format=text&MAKE_EPHEM='YES'&EPHEM_TYPE='OBSERVER'&COORD_TYPE='GEODETIC'&CENTER='coord@399'&REF_SYSTEM='ICRF'&CAL_FORMAT='CAL'&CAL_TYPE='M'&TIME_DIGITS='SECONDS'&ANG_FORMAT='DEG'&APPARENT='AIRLESS'&RANGE_UNITS='AU'&SUPPRESS_RANGE_RATE='NO'&SKIP_DAYLT='NO'&SOLAR_ELONG='0,180'&EXTRA_PREC='YES'&R_T_S_ONLY='NO'&CSV_FORMAT='YES'&OBJ_DATA='YES'&",
        "COMMAND=" + "'" + target_body + "'" + "&",
        "SITE_COORD=" + "'" + observer_location + "'" + "&",
        "START_TIME=" + "'" + start_time + "'" + "&",
        "STOP_TIME=" + "'" + stop_time + "'" + "&",
        "STEP_SIZE=" + "'" + step_size + "'" "&",
        "QUANTITIES=" + "'" + quantities + "'" ]
    url = ''.join( url ).replace(" ", "%20")
    response = urllib.request.urlopen( url ).read().decode( 'UTF-8' )
    validate_ephemeris_data( response )
    return response


def validate_ephemeris_data( response ) -> None:
    """
    Identify and intercept common errors before returning ephemeris string to client.
    :param response: String of text returning from NASA/JPL Horizons API query
    :return: None if response contains no errors. Else, exception raised.
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
        raise SystemError( p + "'Unknown units specification -- re-enter'. Check step_size argument format." )
    if "exceeds 90024 line max -- change step-size" in response:
        raise SystemError( p + "'Projected output length... exceeds 90024 line max -- change step-size'. Horizons prints a 90024 entry maximum." )
    if "Unknown quantity requested" in response:
        raise SystemError( p + "'Unknown quantity requested'. Check 'quantity' argument for recovering JPL ephemeris." )
    if "$$SOE" not in response:
        raise SystemError( "NASA/JPL Horizons API response invalid. Check sunspot.Ephemeris argument format." )


def validate_jpl_ephemeris_date(t):
    from datetime import datetime
    try:
        d = datetime.strptime( convert_numeric_month(t), DATA_FORMAT )
    except ValueError as e:
        raise SystemError( "Invalid date format! Dates must be in format YYYY-MM-DD HH:MM:SS as 24h clock." ) from e
    if d.timestamp() < datetime.strptime( '1599-12-10 23:59:00', DATA_FORMAT ).timestamp():
        raise SystemError( "Earliest accessible JPL Ephemeris date is 1599-12-10 23:59:00." )
    if d.timestamp() > datetime.strptime( '2500-12-31 23:58:00', DATA_FORMAT ).timestamp():
        raise SystemError( "Most distant accessible JPL Ephemeris date is 2500-12-31 23:58:00." )


def validate_jpl_ephemeris_step_unit( u ):
    error = "Invalid step unit label. Check Check step_size argument format."
    try:
        if not VALID_STEP_LABELS.__contains__( u.split( ' ' )[1] ):
            raise SystemError( error )
    except IndexError:
        raise SystemError( error )


def fixture() -> Ephemeris:
    return Ephemeris( '1988-12-08 01:02:03', '1990-04-22 04:05:06', '-71.332597,42.458790,0.041', '1 day', '10' )


def terminal_print( e = fixture() ):
    for i in e.DATA_ENTRIES_RAW:
        print( i )
