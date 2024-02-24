from simulator import SimpleSingleTickerSimulator

class SimpleExecutor1(SimpleSingleTickerSimulator):
    """
    BOT1 is a market-making bot designed for a single ticker. It makes trading decisions 
    based on market conditions and inventory levels to optimize order placement and management.
    """
    def __init__(self, ticker, order_size_ratio=0.1, **kwargs):
        """
        Initializes the bot with specific trading parameters.

        :param ticker: The ticker symbol for trading.
        :param order_size_ratio: Ratio to determine the size of the orders.
        """
        super().__init__(ticker, **kwargs)
        self.order_size_ratio = order_size_ratio

    def run_algo(self, bid_orderbook, ask_orderbook, inventory, bid_orders, ask_orders):
        """
        Main algorithm function for making trading decisions.
        """
        self.manage_orders(bid_orderbook, ask_orderbook, bid_orders, ask_orders)
        self.adjust_orders_based_on_market(bid_orderbook, ask_orderbook, inventory, bid_orders, ask_orders)

    def manage_orders(self, bid_orderbook, ask_orderbook, bid_orders, ask_orders):
        """
        Manages existing orders, canceling those that are outside the top levels of the orderbook.
        """
        self.cancel_orders_outside_top_levels(bid_orderbook, bid_orders, 'BID')
        self.cancel_orders_outside_top_levels(ask_orderbook, ask_orders, 'ASK')

    def cancel_orders_outside_top_levels(self, orderbook, orders, side):
        """
        Cancels orders that are outside the top levels of the order book.
        """
        for price in list(orders.keys()):
            if not self.is_order_within_top_levels(price, orderbook, side):
                self.cancel_order(price, side=side)

    def is_order_within_top_levels(self, price, orderbook, side):
        if side == 'ASK':
            top_level_price = orderbook[0][0]
            bottom_level_price = orderbook[self.NO_OF_ORDERBOOK_LEVELS - 1][0]
            return top_level_price <= price <= bottom_level_price
        elif side == 'BID':
            top_level_price = orderbook[0][0]
            bottom_level_price = orderbook[self.NO_OF_ORDERBOOK_LEVELS - 1][0]
            return top_level_price >= price >= bottom_level_price
        else:
            raise ValueError('Invalid Side??')

    def is_order_better_than_best(self, price, orderbook, side):
        if side == 'ASK':
            top_level_price = orderbook[0][0]
            return top_level_price > price 
        elif side == 'BID':
            top_level_price = orderbook[0][0]
            return top_level_price < price 
        else:
            raise ValueError('Invalid Side??')


    def place_or_adjust_order(self, orderbook, orders, inventory, side, target_price):
        """
        Places or adjusts an order at a target price.
        """
        target_price = round(target_price,  2)
        if self.is_order_better_than_best(target_price, orderbook, side):
            target_price = orderbook[0][0]

        if len(orders) == 0:
            if self.is_order_within_top_levels(target_price, orderbook, side):
                size = self.calculate_order_size(orderbook, inventory, side)
                self.place_order(target_price, size, side=side)

        elif len(orders) == 1:
            order_price = list(orders.keys())[0]
            if abs(order_price - target_price) >= 0.02:
                self.cancel_order(order_price, side=side)
                if self.is_order_within_top_levels(target_price, orderbook, side):
                    size = self.calculate_order_size(orderbook, inventory, side)
                    self.place_order(target_price, size, side=side)
                
    def calculate_order_size(self, orderbook, inventory, side):
        """
        Calculates order size dynamically based on market depth and inventory.
        """
        market_depth_size = orderbook[1][1]  # Using level 1 for size reference
        return min(int(market_depth_size * self.order_size_ratio), 100)

    def adjust_orders_based_on_market(self, bid_orderbook, ask_orderbook, inventory, bid_orders, ask_orders):
        """
        Adjusts the orders based on the current market conditions.
        """
        bid_price, ask_price = self.calculate_bid_ask_price(bid_orderbook, ask_orderbook, inventory)
        self.place_or_adjust_order(bid_orderbook, bid_orders, inventory, 'BID', bid_price)
        self.place_or_adjust_order(ask_orderbook, ask_orders, inventory, 'ASK', ask_price)

    def calculate_bid_ask_price(self, ask_orderbook, bid_orderbook, inventory):
        """
        Compute the bid and ask prices based on orderbook status and inventory
        Needs to be overwritten by the model
        """
        spread = ask_orderbook[0][0] - bid_orderbook[0][0]
        mid_price = (ask_orderbook[0][0] + bid_orderbook[0][0])/2
        raise ValueError('Not Implemented! Function calculate_bid_ask_price needs to be written by the model class.')        
        pass
