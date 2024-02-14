import databento as db
import pandas as pd

def databento_file_parser(file_path):

    stored_data = db.DBNStore.from_file(file_path)

    # Convert to dataframe
    df = stored_data.to_df()
    df = df[df.publisher_id == 2]
    del df['publisher_id']
    del df['rtype']
    del df['ts_in_delta']
    del df['instrument_id']
    del df['sequence']

    for i in range(10):
        del df[f'bid_ct_{i:02.0f}']
        del df[f'ask_ct_{i:02.0f}']

    df.index = df.index.tz_localize(None)
    df['ts_event'] = df['ts_event'].dt.tz_localize(None)

    open_ts = pd.to_datetime(str(df.ts_event.iloc[0].date()) + ' 14:30:00')
    df = df[df['ts_event'] > open_ts]

    close_ts = pd.to_datetime(str(df.ts_event.iloc[0].date()) + ' 21:00:00')
    df = df[df['ts_event'] < close_ts]

    return df
