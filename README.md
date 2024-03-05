# Market Making Simulator
This is a complete backtesting framework to test and build market making strategies on historical limit order book data. 
- Bridge Theory with Practice: Close the gap between theoretical market-making research and real-world applications by leveraging high-frequency data.

- Open-Source Framework: Develop an open-source back-testing and analytics framework for market-making models, enhancing accessibility and collaboration in the field.

## Features
- Customizable Parameters: Enable users to fine-tune their market-making models by adjusting parameters such as latency and sizing within the framework.

- Modular Structure: Whole framework is built to be modular, such that the user can change anything from the queueing logic to fill generation.

- Optimized Traditional Models: Implement traditional market-making models and refine them with optimized hyperparameters tailored to individual stock behaviors.

- Empirical Analysis Tools: Provide a comprehensive framework for empirical analysis and backtesting, facilitating thorough evaluation and validation of market-making strategies.

## Major Components

- `data_parser`: Functions to parse and organize the data in a standardized format which can be understood by the rest of the framework. The current function `databento_file_parser`, works for the databento data we used on our project. 

- `simulator/SimulatorBase`: Core logic of the simulator to process market events and recreate the limit orderbook. 

- `simulator/SimpleSingleTickerSimulator`: Implements the queueing logic and time priority. Also handles the fill generation for the marker making bot. 

- `executor/SimpleExecutor1`: Executors act as an interface between a market making model which just spits out bid and ask price to a BOT which places and cancels orders in the market. 

## How to use the framework

### Run market making model
```
from executor import SimpleExecutor1
class BOT1(SimpleExecutor1):

    def calculate_bid_ask_price(self, bid_orderbook, ask_orderbook, inventory):
        """
        Place orders at the level 1 of the orders. 
        """
        return bid_orderbook[1][0], ask_orderbook[1][0]

# Instantiate and run the bot
bot1 = BOT1(ticker='AMZN')
bot1.run_sim(amzn_df)
```

### Make custom executor
```
from simulator import SimpleSingleTickerSimulator
class BOT1(SimpleSingleTickerSimulator):

    def run_algo(self, bid_orderbook, ask_orderbook, inventory, bid_orders, ask_orders):
        """
        Place order on both sides at level 0 of size 1
        """
        self.place_order(self, bid_orderbook[0][0], 1, side='BID')
        self.place_order(self, ask_orderbook[0][0], 1, side='ASK')

# Instantiate and run the bot
bot1 = BOT1(ticker='AMZN')
bot1.run_sim(amzn_df)
```

## Reference Notebooks

- `notebooks\simulation_example.ipynb`
- `notebooks\executor_example.ipynb`
- `notebooks\model_avellaneda_a.ipynb`
- `notebooks\model_avellaneda_b.ipynb`
- `notebooks\model_ho_and_stoll.ipynb`
- `notebooks\summary_statistics.ipynb`

## Setup
Any standard python environment will work. We will setup the detailed package requirements later.

Install databento package to support using databento data:
```
pip install databento
```
