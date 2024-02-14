import pandas as pd
import math

class SimulatorBase:

    # Number of order book levels
    NO_OF_ORDERBOOK_LEVELS = 10
    
    # price -> size; There are the algo's orders
    BID_ALGO_ORDERS = {}
    ASK_ALGO_ORDERS = {}
    
    # Algo current position
    ALGO_POSITION = 0

    # Algo fills
    ALGO_FILLS = []
    
    # Level -> (price, size); The combined market orderbook with simulator orders
    BID_SIM_ORDER_BOOK = {}
    ASK_SIM_ORDER_BOOK = {}
    
    # Track timestamp
    current_ts = pd.to_datetime('1970-01-01')
    
    def __init__(self, ticker):
        self.ticker = ticker
        
    def process_orderbook_update(self, raw_orderbook_row):
        
        timestamp = raw_orderbook_row['ts_event']
        action = raw_orderbook_row['action']        
        
        if self.current_ts == 0:
            self.current_ts = timestamp
        
        assert timestamp >= self.current_ts, f"WTF? Trying to go back in time? {timestamp=} {self.current_ts=}"
        
        # Whenever the event type is trade, it doesn't update the orderbook in that event. Wait for the next event for the updated orderbook
        if action == 'T':
            # Create fills for the algo if price matches, else do nothing
            trade_price = raw_orderbook_row['price']
            trade_size = raw_orderbook_row['size']
            trade_depth = raw_orderbook_row['depth']
            
            self.process_trade(trade_price, trade_size, trade_depth)
                    
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

    def process_trade(self, trade_price, trade_size, trade_depth):
        # To be overwritten to create fills
        pass

    def run_sim(self, data_df: pd.DataFrame):
        
        cnt = 0
        for row in data_df.iterrows():
            
            self.process_orderbook_update(row[1])
            
            if row[1]['flags'] >= 128:
                self.run_algo(self.BID_SIM_ORDER_BOOK, self.ASK_SIM_ORDER_BOOK, 
                              self.ALGO_POSITION, 
                              self.BID_ALGO_ORDERS, self.ASK_ALGO_ORDERS)
                
            cnt += 1
            
            if cnt % 50000 == 0:
                print(f"{self.current_ts=} \n{self.BID_SIM_ORDER_BOOK=} \n{self.ASK_SIM_ORDER_BOOK=} \n{self.BID_ALGO_ORDERS=} \n{self.ASK_ALGO_ORDERS=} \n{self.ALGO_POSITION=} \n")

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


class SimpleSingleTickerSimulator(SimulatorBase):

    def process_trade(self, trade_price, trade_size, trade_depth):
        
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

        self.ALGO_FILLS.append((trade_price, executed_size * side))
        self.ALGO_POSITION += executed_size * side
        
        orders_dict[trade_price] -= executed_size
        
        if orders_dict[trade_price] == 0:
            del orders_dict[trade_price]

