import pandas as pd
import numpy as np
import math
from datetime import datetime, timedelta

class SimulatorBase:

    # Number of order book levels
    NO_OF_ORDERBOOK_LEVELS = 10
    
    # Algo current position
    ALGO_POSITION = 0
    
    # Marker Making Params
    data_df = None
    current_ts = pd.to_datetime('1970-01-01')
    time_frac_elapsed = 0
    sigma_1min = 0.1
    sigma_5min = 0.1
    sigma_15min = 0.1

    def __init__(self, ticker, verbose=True, print_freq=50000):
        self.ticker = ticker
        self.verbose = verbose
        self.print_freq = print_freq

        # Explicitly initialize mutable types

        # price -> size; There are the algo's orders
        self.BID_ALGO_ORDERS = {}
        self.ASK_ALGO_ORDERS = {}
        
        # Level -> (price, size); The combined market orderbook with simulator orders
        self.BID_SIM_ORDER_BOOK = {}
        self.ASK_SIM_ORDER_BOOK = {}

        # Monitoring and results
        self.BOT_FILLS = []
        self.BOT_QUOTES = []
        self.output_data = {}


    def is_verbose_cnt(self):
        return self.verbose and self.cnt % self.print_freq == 0

    def process_orderbook_update(self, raw_orderbook_row):
        
        timestamp = raw_orderbook_row['ts_event']
        action = raw_orderbook_row['action']        
        midprice = (raw_orderbook_row['bid_px_00'] + raw_orderbook_row['ask_px_00'])/2        

        if self.current_ts == 0:
            self.current_ts = timestamp
        
        assert timestamp >= self.current_ts, f"WTF? Trying to go back in time? {timestamp=} {self.current_ts=}"
        
        # Whenever the event type is trade, it doesn't update the orderbook in that event. Wait for the next event for the updated orderbook
        if action == 'T':
            # Create fills for the algo if price matches, else do nothing
            trade_price = raw_orderbook_row['price']
            trade_size = raw_orderbook_row['size']
            trade_depth = raw_orderbook_row['depth']
            
            self.process_trade(trade_price, trade_size, trade_depth, midprice)
                    
        # For now treat all other actions as same. Just construct the combined market and algo orderbook
        # TODO: Add queue position logic and compute position better using ADD and CANCEL events
        else:
            self.construct_combined_orderbook(raw_orderbook_row)            
        self.current_ts = timestamp
   
    def construct_combined_orderbook(self, raw_orderbook_row):

        self.BID_SIM_ORDER_BOOK = {}
        self.ASK_SIM_ORDER_BOOK = {}
        
        for i in range(self.NO_OF_ORDERBOOK_LEVELS):    
            bid_px = raw_orderbook_row[f'bid_px_{i:02.0f}']
            ask_px = raw_orderbook_row[f'ask_px_{i:02.0f}']
            bid_sz = raw_orderbook_row[f'bid_sz_{i:02.0f}']
            ask_sz = raw_orderbook_row[f'ask_sz_{i:02.0f}']
            
            bid_sz += self.BID_ALGO_ORDERS.get(bid_px, 0)
            ask_sz += self.ASK_ALGO_ORDERS.get(ask_px, 0)
            
            self.BID_SIM_ORDER_BOOK[i] = (bid_px, bid_sz)
            self.ASK_SIM_ORDER_BOOK[i] = (ask_px, ask_sz)

    def save_bot_quotes(self, raw_orderbook_row):        

        best_bid = raw_orderbook_row[f'bid_px_00']
        best_ask = raw_orderbook_row[f'ask_px_00']

        bid = np.nan
        ask = np.nan

        if self.BID_ALGO_ORDERS:
            bid = max(self.BID_ALGO_ORDERS.keys())

        if self.ASK_ALGO_ORDERS:
            ask = max(self.ASK_ALGO_ORDERS.keys())

        quote = {'ts': self.current_ts,
                 'best_bid': best_bid, 
                 'best_ask': best_ask, 
                 'bid': bid, 
                 'ask': ask}
        
        prev_quote = self.BOT_QUOTES[-1] if self.BOT_QUOTES else {'bid': 0, 'ask': 0}
        if prev_quote['bid'] != quote['bid'] or prev_quote['ask'] != quote['ask']:
            self.BOT_QUOTES.append(quote)

    def process_trade(self, trade_price, trade_size, trade_depth, midprice):
        # To be overwritten to create fills
        pass

    def run_sim(self, data_df: pd.DataFrame):
        
        self.cnt = 0
        self.data_df = data_df
        self.pre_compute_static_params(data_df)

        for row in data_df.iterrows():
            
            self.process_orderbook_update(row[1])

            if self.cnt % 100 == 0:
                self.update_params(data_df)

            self.save_bot_quotes(row[1])

            if row[1]['flags'] >= 128:
                self.run_algo(self.BID_SIM_ORDER_BOOK, self.ASK_SIM_ORDER_BOOK, 
                              self.ALGO_POSITION, 
                              self.BID_ALGO_ORDERS, self.ASK_ALGO_ORDERS)
                                
            self.cnt += 1

            if self.is_verbose_cnt():
                print(f"{self.current_ts=} \n{self.BID_SIM_ORDER_BOOK=} \n{self.ASK_SIM_ORDER_BOOK=} \n{self.BID_ALGO_ORDERS=} \n{self.ASK_ALGO_ORDERS=} \n{self.ALGO_POSITION=} \n")

        self.build_output_data()

    ## Interface for the BOT
    def place_order(self, price, size, side='ASK'):
        
        if side == 'ASK':
            orderbook_dict = self.ASK_ALGO_ORDERS
        else:
            orderbook_dict = self.BID_ALGO_ORDERS
            
        orderbook_dict[price] = size

    def cancel_order(self, price, side='ASK'):
        
        if side == 'ASK':
            orderbook_dict = self.ASK_ALGO_ORDERS
        else:
            orderbook_dict = self.BID_ALGO_ORDERS
        
        if price in orderbook_dict:
            del orderbook_dict[price]

    #To be overwritten by the Executor Class
    def run_algo(self, bid_orderbook, ask_orderbook, inventory, bid_orders, ask_orders):
        pass

    ## Additional params for models
    def update_params(self, data_df):

        start_ts = data_df['ts_event'].iloc[0]
        end_ts = data_df['ts_event'].iloc[-1]
        
        self.time_frac_elapsed = (self.current_ts - start_ts) / (end_ts - start_ts)
        ts = self.current_ts.floor('s')

        if ts in self.static_params_df.index:
            row = self.static_params_df.loc[ts]
            self.sigma_1min = row['sigma_1min']
            self.sigma_5min = row['sigma_5min']
            self.sigma_15min = row['sigma_15min']

    def pre_compute_static_params(self, data_df):
        
        df = data_df[['bid_px_00', 'ask_px_00']]
        df = df.reset_index().drop_duplicates(subset='ts_recv', keep='first').set_index('ts_recv')
        df = df.resample('1s').last().ffill()
        df['midprice'] = df.mean(axis=1)

        scaling = 1

        df['sigma_1min'] = df['midprice'].rolling(window='1min').std() * scaling
        df['sigma_5min'] = df['midprice'].rolling(window='5min').std() * scaling
        df['sigma_15min'] = df['midprice'].rolling(window='15min').std() * scaling
        self.static_params_df = df

    def build_output_data(self):

        trades_df = pd.DataFrame(self.BOT_FILLS)
        quotes_df = pd.DataFrame(self.BOT_QUOTES)
        
        capital = (trades_df['price'] * trades_df['size']).sum() * -1
        position = trades_df['size'].sum()            

        trading_volume = trades_df['size'].abs().sum()
        rebate = 0.01 * trading_volume
        pnl = capital + position * self.BOT_FILLS[-1]['price'] + rebate
        trading_pnl = ((trades_df['midprice'] - trades_df['price']) * trades_df['size']).sum() + rebate

        time = trades_df['ts'].diff().dt.total_seconds().shift(-1) 
        avg_size = (time * trades_df['size'].abs()).sum() / time.sum()        
        avg_size_square = (time * trades_df['size'].abs().pow(2)).sum() / time.sum()
        
        volatility = self.static_params_df['sigma_1min'].mean()
        net_return = self.static_params_df['midprice'].iloc[0] - self.static_params_df['midprice'].iloc[-1]

        print(f"{capital=} {position=} {pnl=} {trading_pnl=} {trading_volume=} {avg_size=} {avg_size_square=}")

        self.output_data['eod_position'] = position
        self.output_data['eod_cash'] = capital
        self.output_data['net_pnl'] = pnl
        self.output_data['trading_pnl'] = trading_pnl
        self.output_data['avg_size'] = avg_size
        self.output_data['avg_size_square'] = avg_size_square
        self.output_data['trading_volume'] = trading_volume

        self.output_data['volatility'] = volatility
        self.output_data['net_return'] = net_return

        self.output_data['trades'] = trades_df
        self.output_data['quotes'] = quotes_df



class SimpleSingleTickerSimulator(SimulatorBase):

    def process_trade(self, trade_price, trade_size, trade_depth, midprice):
        
        if trade_price in self.BID_ALGO_ORDERS:
            orders_dict = self.BID_ALGO_ORDERS
            orderbook_dict = self.BID_SIM_ORDER_BOOK
            side = 1
            
        elif trade_price in self.ASK_ALGO_ORDERS:
            orders_dict = self.ASK_ALGO_ORDERS
            orderbook_dict = self.ASK_SIM_ORDER_BOOK
            side = -1
        
        else:
            return

        order_size = orders_dict[trade_price]
        book_size = orderbook_dict[trade_depth][1]
        
        # Assume our fill is the fraction of the book this trade cleared
        executed_size = math.ceil(order_size * min(trade_size / book_size, 1))

        # Record this fill
        self.BOT_FILLS.append({'ts': self.current_ts, 
                               'price': trade_price, 
                               'size': executed_size * side, 
                               'midprice': midprice})

        # Update position/inventory
        self.ALGO_POSITION += executed_size * side
        
        orders_dict[trade_price] -= executed_size
        
        if orders_dict[trade_price] == 0:
            del orders_dict[trade_price]

