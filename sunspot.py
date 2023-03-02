"""
Sunspot: ephemeris engine for automated telescope guidance

Powered by NASA/JPL Horizons Ephemeris API, which is not affiliated with Sunspot.
For NASA/JPL informations, see: https://ssd.jpl.nasa.gov/horizons/manual.html#center
"""


class Ephemeris:

    DATA_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(self, start_time: str, stop_time: str, observer_location: str, step_size: str, target_body: str ):
        """

        :param start_time:
        :param stop_time:
        :param observer_location:
        :param step_size:
        :param target_body:
        """
        self.RAW_DATA = get_jpl_ephemeris( start_time, stop_time, observer_location, step_size, target_body )
        self.RAW_DATA_LINES = self.RAW_DATA.split( "\n" )

    def data_column_headers( self ) -> list:
        """
        :return: A list of data column headers.
        """
        import re as regex
        return regex.split( '[ ]+', self.RAW_DATA_LINES[ self.RAW_DATA_LINES.index("$$SOE") - 2 ] )[1:]

    def ephemeris_data_rows( self ) -> list:
        """
        :return: A list of strings of ephemeris data, where each list entry is a row of data for a given time. Omits header and footer.
        """
        rows = self.RAW_DATA_LINES[ self.RAW_DATA_LINES.index("$$SOE") + 1 : self.RAW_DATA_LINES.index("$$EOE") ]
        for i, row in enumerate( rows ):
            rows[i] = row[1:] # clip leading space from all rows
        return rows

    def parsed_ephemeris_data( self ) -> dict:
        """
        :return: A dictionary of ephemeris data, where keys are #get_ephemeris_data_column_headers and each value is a list of data corresponding to that header. Entries in each list are in chronological order.
        """
        import re as regex
        # from datetime import datetime # TODO not used if conversion omitted
        from collections import defaultdict
        rows = self.ephemeris_data_rows()
        column_headers = self.data_column_headers()
        ephemeris = defaultdict( list )
        for i, row in enumerate( rows ):
            # row = convert_numeric_month( row ) # TODO conduct conversion later?
            row_items = regex.split( '[ ]+', row )
            # ephemeris[ column_headers[0] ].append( datetime.strptime( row_items[0] + " " + row_items[1], self.DATA_FORMAT ) ) # TODO conduct conversion later?
            ephemeris[ column_headers[0] ].append( row_items[0] + " " + row_items[1] )
            ephemeris[ column_headers[1] ].append( [ row_items[3], row_items[4] ] )
            ephemeris[ column_headers[2] ].append( [ row_items[5], row_items[6] ] )
        return ephemeris

    def get_ephemeris_data( self, column_header: str ) -> list:
        """
        :param column_header: String header corresponding to a column of ephemeris data, e.g., "Date__(UT)__HR:MN:SS"
        :return: A list of data corresponding to an ephemeris data column header. Entries in this list are in chronological order.
        """
        if not self.data_column_headers().__contains__( column_header ):
            raise SystemError( "Method argument must be an ephemeris data column header." )
        return self.parsed_ephemeris_data().get(column_header)

    def dates( self ) -> list:
        """
        :return: A list of ephemeris dates, in chronological order.
        """
        return self.get_ephemeris_data( 'Date__(UT)__HR:MN:SS' )

    def azimuth_elevation_coordinates( self ) -> list:
        """
        :return: A list of azimuth-elevation coordinate pairs, in chronological order. Each pair is a list of length 2.
        """
        return self.get_ephemeris_data( 'Azi____(a-app)___Elev' )

    def right_ascension_declination_coordinates( self ) -> list:
        """
        :return: A list of right-ascension-declination coordinate pairs, in chronological order. Each pair is a list of length 2.
        """
        return self.get_ephemeris_data( 'R.A._(a-appar)_DEC.' )

    def find_corresponding_data( self, target_data_column_header: str, source_data_column_header: str, source_data_point: str ):
        """
        Retrieve data point from within target_data_column, corresponding to source_data_point from within source_data_column.
        :param target_data_column_header: String header corresponding to a column of ephemeris data in which to search, e.g., "Azi____(a-app)___Elev"
        :param source_data_column_header: String header corresponding to a column of ephemeris data from where search datum originates, e.g., "Date__(UT)__HR:MN:SS"
        :param source_data_point: String datum found within source_data_column for which a corresponding row returns.
        :return: Datum from row of target_data_column, from where source_data_point is found in source_data_column. If source_data_point not found in source_data_column, returns None.
        """
        source_data = self.get_ephemeris_data( source_data_column_header )
        if not source_data.__contains__( source_data_point ):
            return None
        target_data = self.get_ephemeris_data( target_data_column_header )
        return target_data[ source_data.index(source_data_point) ]



class Tracker:
    def __init__( self, e: Ephemeris ):
        pass


def convert_numeric_month( r ) -> str:
    return r.replace( "Jan", "01" ).replace( "Feb", "02" ).replace( "Mar", "03" ).replace( "Apr", "04" ).replace( "May", "05" ).replace( "Jun", "06" ).replace( "Jul", "07" ).replace( "Aug", "08" ).replace( "Sep", "09" ).replace( "Oct", "10" ).replace( "Nov", "11" ).replace( "Dec", "12" )


def get_jpl_ephemeris(  start_time: str,  # 'YYYY-MM-DD HH:MM:SS' See: https://ssd.jpl.nasa.gov/tools/jdc/#/cd
                        stop_time: str,
                        observer_location: str,  # '00,00,00' as 'latitude [fractional degrees], longitude [fractional degrees], elevation [km]'
                        step_size: str,  # e.g., "1 d"
                        target_body: str ) -> str: # E.g. 'Sol' is the sun. Search target_bodies here: https://ssd.jpl.nasa.gov/horizons/app.html#/
    # TODO add method(s) to check/format str arguments for cases where JPL accepts several argument variants, e.g., reformat HH:MM as HH:MM:SS
    import urllib.request
    url = [
        "https://ssd.jpl.nasa.gov/api/horizons.api?format=text&MAKE_EPHEM='YES'&EPHEM_TYPE='OBSERVER'&COORD_TYPE='GEODETIC'&CENTER='coord@399'&QUANTITIES='2,4'&REF_SYSTEM='ICRF'&CAL_FORMAT='CAL'&CAL_TYPE='M'&TIME_DIGITS='MINUTES'&ANG_FORMAT='DEG'&APPARENT='AIRLESS'&RANGE_UNITS='AU'&SUPPRESS_RANGE_RATE='NO'&SKIP_DAYLT='NO'&SOLAR_ELONG='0,180'&EXTRA_PREC='NO'&R_T_S_ONLY='NO'&CSV_FORMAT='NO'&OBJ_DATA='YES'&",
        "COMMAND=" + "'" + target_body + "'" + "&",
        "SITE_COORD=" + "'" + observer_location + "'" + "&",
        "START_TIME=" + "'" + start_time + "'" + "&",
        "STOP_TIME=" + "'" + stop_time + "'" + "&",
        "STEP_SIZE=" + "'" + step_size + "'"]
    url = ''.join( url )
    url = url.replace(" ", "%20")
    response = urllib.request.urlopen( url )
    response = response.read().decode( 'UTF-8' )
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
        raise SystemError( p + "'Unknown units specification -- re-enter'. Check Step_Size argument format." )
    if "exceeds 90024 line max -- change step-size" in response:
        raise SystemError( p + "'Projected output length... exceeds 90024 line max -- change step-size'. Horizons prints a 90024 entry maximum." )