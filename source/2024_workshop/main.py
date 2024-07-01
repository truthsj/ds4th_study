import pandas as pd
from pykrx import stock
from stock_trading_env import StockTradingEnv
from dqn_agent import DQNAgent
import numpy as np 

def get_stock_data(ticker, start_date, end_date):
    """
    주어진 티커와 날짜 범위에 대한 주식 데이터를 가져옵니다.

    Args:
        ticker (str): 주식 티커
        start_date (str): 시작 날짜 (YYYY-MM-DD)
        end_date (str): 종료 날짜 (YYYY-MM-DD)

    Returns:
        DataFrame: 주식 데이터
    """
    df = stock.get_market_ohlcv_by_date(start_date, end_date, ticker)
    df.reset_index(inplace=True)
    df.rename(columns={'날짜': 'Date', '종가': 'Close', '시가': 'Open', '고가': 'High', '저가': 'Low', '거래량': 'Volume'}, inplace=True)
    return df

# 사용 예시
ticker = "005930"  # 삼성전자
start_date = "2023-01-01"
end_date = "2023-12-31"
stock_data = get_stock_data(ticker, start_date, end_date)

# 강화학습 환경 및 에이전트 초기화
env = StockTradingEnv(stock_data)
state_size = 3
action_size = 3
agent = DQNAgent(state_size, action_size)

# 강화학습 에피소드 및 학습
EPISODES = 1000
batch_size = 32

for e in range(EPISODES):
    state = env.reset()
    state = np.reshape(state, [1, state_size])
    for time in range(env.total_steps):
        action = agent.act(state)
        next_state, reward, done, _ = env.step(action)
        reward = reward if not done else -10
        next_state = np.reshape(next_state, [1, state_size])
        agent.remember(state, action, reward, next_state, done)
        state = next_state
        if done:
            print(f"episode: {e+1}/{EPISODES}, score: {reward}, epsilon: {agent.epsilon}")
            break
        if len(agent.memory) > batch_size:
            agent.replay(batch_size)
