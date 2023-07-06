"""
Sunspot: Simple and light-weight JPL ephemeris parser and tracking engine for astronomy and telescope guidance. Provides simple lists of ephemeris data for any Target Body available through the JPL Horizons App. Also provides real-time tracking of those data for the duration of an ephemeris.

Powered by NASA/JPL Horizons Ephemeris API, which is not affiliated with Sunspot.
For NASA/JPL information, see: https://ssd.jpl.nasa.gov/horizons/manual.html#center

__author__ = "Phillip Curtsmith"
__copyright__ = "Copyright 2023, Phillip Curtsmith"

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
        :param quantities: observer quantities from JPL index, here: https://ssd.jpl.nasa.gov/horizons/app.html#/ . Default includes right ascension, declination, and altitude/azimuth
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
        from datetime import datetime
        ephemeris = defaultdict( list )
        for row in self.DATA_ENTRIES:
            row_items = row.split( ',' )
            row_items = [ i.strip(' ') for i in row_items ]
            row_items = [ i for i in row_items if i not in SOLAR_AND_LUNAR_PRESENCE_SYMBOLS ]
            for column in range( len(self.DATA_TITLES) ):
                ephemeris[ self.DATA_TITLES[column] ].append( row_items[column] )
        # Scrub dates to include numeric months rather than strings, e.g., 'Feb' becomes '02'
        dates = ephemeris.get( self.DATA_TITLES[0] )
        for k, entry in enumerate( dates ):
            dates[k] = convert_numeric_month( entry )
        # JPL omits 'seconds' unit completely if user enters HH:MM:SS where SS=00. If present, fix.
        try:
            datetime.strptime( dates[0], DATA_FORMAT )
        except ValueError:
            zeros = ":00"
            for k, entry in enumerate( dates ):
                dates[k] = entry + zeros
        return ephemeris

    def get_ephemeris_data( self, column_title: str ) -> list:
        """
        :param column_title: String title corresponding to a column of ephemeris data, e.g., "Date__(UT)__HR:MN:SS" or Ephemeris.DATA_TITLES[n] where n is a valid index.
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

    def __init__( self, e: Ephemeris,
                  track_before_method: callable( list ) = None,
                  track_on_time_method: callable( list ) = None,
                  track_after_method: callable( list ) = None,
                  verbose: bool = False ):
        """
        Create Tracker object. Tracking begins automatically upon object creation. Tracker objects will automatically track beginning with the next-soonest date. If no next-soonest date, e.g., all dates are in past, SystemError results.
        :param e: Ephemeris object.
        :param track_before_method: User-defined method. Must accept list of strings corresponding to Ephemeris _Observer Quantities_. Optional argument.
        :param track_on_time_method: User-defined method. Must accept list of strings corresponding to Ephemeris _Observer Quantities_. Optional argument.
        :param track_after_method: User-defined method. Must accept list of strings corresponding to Ephemeris _Observer Quantities_. Optional argument.
        :param verbose: If True, prints method execution time stamps to terminal.
        """
        self.verbose = verbose
        self.ephemeris = e
        starting_index = self.next_event_index( e )
        if starting_index is None:
            raise SystemError( "All Ephemeris entries are in the past! One cannot track past events." )
        if self.verbose:
            print( "First scheduled tracking event: [" + e.dates()[starting_index] + "]" )

        # Start tracking thread
        import threading
        import signal
        self.exit_event_trigger = threading.Event()
        signal.signal( signal.SIGINT, self.terminate_tracking )
        self.c = threading.Thread( target = self.track, args = [ track_before_method,
                                                                 track_on_time_method,
                                                                 track_after_method,
                                                                 starting_index ] )
        self.c.start()

    def terminate_tracking( self ) -> None:
        """
        Terminate tracking for a current Tracker object.
        :return: None
        """
        self.exit_event_trigger.set()

    def user_cancelled_tracking( self ) -> bool:
        if self.exit_event_trigger.is_set():
            if self.verbose:
                print( "SUNSPOT#TRACKER: Tracking cancelled by user." )
            return True
        return False

    def track( self, before_method, on_time_method, after_method, starting_index ):
        from datetime import datetime
        count = starting_index
        dates = self.ephemeris.dates()
        for i in range( starting_index, len( dates ) ):
            method_arguments = self.collate_arguments( count )
            #
            # CALL BEFORE_METHOD
            #
            if self.user_cancelled_tracking():
                break
            if before_method is not None:
                if self.verbose:
                    print( "SUNSPOT#TRACKER#CALL-BEFORE: Scheduled event [" + dates[count] + "] executed at [" + f'{datetime.now():%Y-%m-%d %H:%M:%S%z}' + "]." )
                before_method( method_arguments )
            #
            # DELAY
            #
            if self.exit_event_trigger.wait( timeout = sleep_time( dates[count] ) ):
                if self.verbose:
                    print( "SUNSPOT#TRACKER: Tracking cancelled by user." )
                break
            #
            # CALL ON_TIME_METHOD
            #
            if self.user_cancelled_tracking():
                break
            if on_time_method is not None:
                if self.verbose:
                    print( "SUNSPOT#TRACKER#CALL-ON-TIME: Scheduled event [" + dates[count] + "] executed at [" + f'{datetime.now():%Y-%m-%d %H:%M:%S%z}' + "]." )
                on_time_method( method_arguments )
            #
            # CALL AFTER_METHOD
            #
            if self.user_cancelled_tracking():
                break
            if after_method is not None:
                if self.verbose:
                    print( "SUNSPOT#TRACKER#CALL-AFTER: Scheduled event [" + dates[count] + "] executed at [" + f'{datetime.now():%Y-%m-%d %H:%M:%S%z}' + "]." )
                after_method( method_arguments )
            #
            count = count + 1
        if not self.exit_event_trigger.is_set():
            if self.verbose:
                print( "SUNSPOT#TRACKER: Ephemeris tracking completed normally at [" + f'{datetime.now():%Y-%m-%d %H:%M:%S%z}' + "]." )

    def collate_arguments( self, count ) -> list:
        args = []
        for i in self.ephemeris.DATA_TITLES:
            args.append( self.ephemeris.get_ephemeris_data(i)[ count ] )
        return args

    def next_event_index( self, e: Ephemeris ):
        from datetime import datetime
        dates = e.dates()
        for i in dates:
            if datetime.now().timestamp() < datetime.strptime( i, DATA_FORMAT ).timestamp():
                return dates.index( i )
        return None


def sleep_time( future, verbose ) -> float:
    """
    :return: The difference, in seconds, between the moment this function is called and the (future) datetime passed as argument.
    If return value is negative (e.g., an event presumed to be in the future is actually in the past), throws exception.
    """
    from datetime import datetime
    if verbose:
        print( "SUNSPOT#TRACKER: Delay event initiated at [" + f'{datetime.now():%Y-%m-%d %H:%M:%S%z}' + "] for future time [" + future + "]." )
    delay = datetime.strptime( future, DATA_FORMAT ).timestamp() - datetime.now().timestamp()
    if delay < 0:
        raise SystemError( "Tracker timing error. attempting to track object at time [" + future + "] indicates this time has already passed. Possibly the result of a long-running user process delaying thread execution." )
    return delay


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
        raise SystemError( "NASA/JPL Horizons API response invalid. Check src.Ephemeris argument format." )


def validate_jpl_ephemeris_date(t):
    from datetime import datetime
    try:
        d = datetime.strptime( t, DATA_FORMAT )
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
