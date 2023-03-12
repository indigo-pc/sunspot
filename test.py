"""
Testing suite for sunspot.py
All tests used live data fixtures
"""

import sunspot
import pytest

FIXTURE_LIST_ALL = ['fixture_default_args', 'fixture_1_args', 'fixture_2_args', 'fixture_2_args_reversed', 'fixture_48_args']
FIXTURE_LIST_PARTIAL = ['fixture_default_args', 'fixture_1_args', 'fixture_2_args', 'fixture_2_args_reversed' ]

@pytest.mark.parametrize( 'fixture', FIXTURE_LIST_ALL )
def test_get_ephemeris_data( fixture, request ):
    """
    Test behavior for invalid #get_ephemeris_data argument
    """
    e = request.getfixturevalue( fixture )
    with pytest.raises( SystemError ):
        e.get_ephemeris_data( 'foo' )


@pytest.mark.parametrize( 'fixture', FIXTURE_LIST_ALL )
def test_corresponding_data_missing_target( fixture, request ):
    """
    Test behavior for invalid #find_corresponding_data argument
    """
    e = request.getfixturevalue( fixture )
    result = e.find_corresponding_data( e.DATA_TITLES[0], e.DATA_TITLES[1], 'foobar' )
    assert( result is None )


@pytest.mark.parametrize( 'fixture', FIXTURE_LIST_ALL )
def test_data_lengths( fixture, request ):
    """
    Check that all vectors from parsed data are correct dimensions.
    """
    e = request.getfixturevalue( fixture )
    known_length = 501
    # Known title counts, verified using JPL online form
    if FIXTURE_LIST_ALL[0] is str( fixture ):
        title_count = 7
    elif FIXTURE_LIST_ALL[1] is str( fixture ):
        title_count = 3
    elif FIXTURE_LIST_ALL[2] is str( fixture ):
        title_count = 5
    elif FIXTURE_LIST_ALL[3] is str( fixture ):
        title_count = 5
    elif FIXTURE_LIST_ALL[4] is str( fixture ):
        title_count = 87
    else:
        raise SystemError( "# # # # UNRECOGNIZED FIXTURE! # # # #" )
    assert( len( e.DATA_ENTRIES ) == known_length )
    assert( len( e.DATA_ENTRIES ) == known_length )
    assert( len( e.dates() ) == known_length )
    assert( len( e.DATA_TITLES ) == title_count )
    assert( e.DATA_TITLES == list( e.PARSED_DATA.keys() ) )
    for j in e.DATA_TITLES:
        assert( len( e.PARSED_DATA.get( j ) ) == known_length )


@pytest.mark.parametrize( 'fixture', FIXTURE_LIST_ALL )
def test_date_order( fixture, request ):
    """
    Check that vector of dates are necessarily in chronological order.
    """
    from datetime import datetime
    e = request.getfixturevalue( fixture )
    dates = e.dates()
    dates = [ sunspot.convert_numeric_month( item ) for item in dates ]
    date_format = sunspot.DATA_FORMAT
    now = datetime.strptime( dates[0], date_format )
    for index, date in enumerate( dates ):
        if index+1 >= len( dates ):
            break
        then = datetime.strptime( dates[index+1], date_format )
        assert( then.timestamp() > now.timestamp() )
        now = then


@pytest.mark.parametrize( 'fixture', FIXTURE_LIST_PARTIAL )
def test_data_date_pairs( fixture, request ):
    """
    Check that each index of non-date vector(s) map onto a corresponding date, and that contiguous indices for that non-date vector are necessarily in chronological order.
    """
    from datetime import datetime
    e = request.getfixturevalue( fixture )
    date_format = sunspot.DATA_FORMAT
    dates_index = 0
    for title_index in range( 1, len( e.DATA_TITLES ) - 1 ):
        for date_index in range( -1, len( e.dates() ) - 2 ):
            # target_data_column_title: str, source_data_column_title: str, source_data_point: str ):
            now = e.find_corresponding_data( e.DATA_TITLES[dates_index], e.DATA_TITLES[title_index], e.get_ephemeris_data( e.DATA_TITLES[title_index] )[date_index+1] )
            now = datetime.strptime( sunspot.convert_numeric_month( now ), date_format )
            then = e.find_corresponding_data( e.DATA_TITLES[dates_index], e.DATA_TITLES[title_index], e.get_ephemeris_data( e.DATA_TITLES[title_index] )[date_index+2] )
            then = datetime.strptime( sunspot.convert_numeric_month( then ), date_format )
            assert( then.timestamp() > now.timestamp() )


@pytest.fixture
def fixture_default_args() -> sunspot.Ephemeris:
    """
    :return: Ephemeris recovers data vectors for a default set of args, e.g., no 5th arg to sunspot.Ephemeris()
    """
    return sunspot.Ephemeris(   '1988-12-08 01:02:03',
                                '1990-04-22 04:05:06',
                                '42.458790,-71.332597,0.041',
                                '1 d',
                                '10')


@pytest.fixture
def fixture_1_args() -> sunspot.Ephemeris:
    """
    :return: Ephemeris recovers only a single data vector (1).
    """
    return sunspot.Ephemeris(   '1988-12-08 01:02:03',
                                '1990-04-22 04:05:06',
                                '42.458790,-71.332597,0.041',
                                '1 d',
                                '10',
                                '1')


@pytest.fixture
def fixture_2_args() -> sunspot.Ephemeris:
    """
    :return: Ephemeris recovers two data vectors (4 and 2)
    """
    return sunspot.Ephemeris(   '1988-12-08 01:02:03',
                                '1990-04-22 04:05:06',
                                '42.458790,-71.332597,0.041',
                                '1 d',
                                '10',
                                '2,4')


@pytest.fixture
def fixture_2_args_reversed() -> sunspot.Ephemeris:
    """
    :return: Ephemeris recovers two data vectors (4 and 2)
    """
    return sunspot.Ephemeris(   '1988-12-08 01:02:03',
                                '1990-04-22 04:05:06',
                                '42.458790,-71.332597,0.041',
                                '1 d',
                                '10',
                                '4,2')


@pytest.fixture
def fixture_48_args() -> sunspot.Ephemeris:
    """
    :return: Ephemeris recovers all 48 possible data types ('1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48')
    """
    return sunspot.Ephemeris(   '1988-12-08 01:02:03',
                                '1990-04-22 04:05:06',
                                '42.458790,-71.332597,0.041',
                                '1 d',
                                '10',
                                '1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48')
