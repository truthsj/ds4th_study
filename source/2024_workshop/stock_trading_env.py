import numpy as np

HOLD = 0
BUY = 1
SELL = 2

class StockTradingEnv:
    def __init__(self, df, initial_balance=1000000, commission_rate=0.00015):
        self.df = df
        self.initial_balance = initial_balance
        self.commission_rate = commission_rate
        self.reset()

    def reset(self):
        self.balance = self.initial_balance
        self.shares_held = 0
        self.current_step = 0
        self.total_steps = len(self.df) - 1
        self.cost_basis = 0
        self.total_trades = 0
        return self._get_observation()    

    def _get_observation(self):
        return np.array([
            self.balance,
            self.shares_held,
            self.cost_basis,
            self.total_trades,
            self.df.iloc[self.current_step]['Close'],
            self.df.iloc[self.current_step]['Open'],
            self.df.iloc[self.current_step]['High'],
            self.df.iloc[self.current_step]['Low'],
            self.df.iloc[self.current_step]['Volume'],
            self.df.iloc[self.current_step]['Rate'], 
            self.df.iloc[self.current_step]['MA20_Simple'],
            self.df.iloc[self.current_step]['MA20_EMA'], 
            self.df.iloc[self.current_step]['MA60_Simple'],
            self.df.iloc[self.current_step]['MA60_EMA']             
        ])
    
    def step(self, action):
        current_price = self.df.loc[self.current_step, 'Close']
        previous_portfolio_value = self.balance + self.shares_held * current_price
        self.current_step += 1
        next_price = self.df.loc[self.current_step, 'Close']
        done = self.current_step == self.total_steps

        # Kelly Criterion parameters (example values, these should be based on your model/strategy)
        b = 1  # Example: 100% expected return
        p = 0.6  # Example: 60% chance of winning (price going up)
        q = 1 - p

        # Calculate the optimal fraction to invest using Kelly Criterion
        f_star = (b * p - q) / b

        if action == BUY:
            balance_to_use = self.balance * f_star
            shares_to_buy = int(balance_to_use // current_price)
            cost = shares_to_buy * current_price
            commission = cost * self.commission_rate
            total_cost = cost + commission

            if total_cost <= self.balance:
                self.balance -= total_cost
                self.shares_held += shares_to_buy
                self.cost_basis = ((self.cost_basis * self.total_trades) + total_cost) / (self.total_trades + 1)
                self.total_trades += 1

        elif action == SELL:
            if self.shares_held > 0:
                shares_to_sell = int(self.shares_held * f_star)
                sale_value = shares_to_sell * current_price
                commission = sale_value * self.commission_rate

                self.balance += sale_value - commission
                self.shares_held -= shares_to_sell
                self.total_trades += 1

        # HOLD action
        else:
            # 홀드 액션에 대한 작은 보상 추가
            hold_reward = 0.0001 * self.balance  # 현재 잔고의 0.01%

        # 포트폴리오 가치 변화 계산
        current_portfolio_value = self.balance + self.shares_held * next_price
        portfolio_return = (current_portfolio_value - previous_portfolio_value) / previous_portfolio_value

        # 개선된 보상 계산
        if action == BUY:
            if next_price > current_price:
                reward = portfolio_return + 0.01  # 성공적인 매수에 대한 추가 보상
            else:
                reward = portfolio_return - 0.01  # 실패한 매수에 대한 페널티
        elif action == SELL:
            if next_price < current_price:
                reward = portfolio_return + 0.01  # 성공적인 매도에 대한 추가 보상
            else:
                reward = portfolio_return - 0.01  # 실패한 매도에 대한 페널티
        else:  # HOLD
            reward = portfolio_return + hold_reward

        # 추가: 과도한 거래에 대한 페널티
        trade_penalty = 0.001 if action != HOLD else 0
        reward -= trade_penalty

        # 리스크 관리: 큰 손실에 대한 추가 페널티
        if portfolio_return < -0.05:  # 5% 이상의 손실
            reward -= 0.1

        return self._get_observation(), reward, done, {}

    def backtest(self, model):
        self.reset()
        done = False
        portfolio_values = [self.initial_balance]
        while not done:
            state = self._get_observation()
            state = np.reshape(state, [1, -1])  # Reshape to match the input shape expected by the model
            action = model.act(state)
            _, reward, done, _ = self.step(action)
            portfolio_value = self.balance + self.shares_held * self.df.loc[self.current_step, 'Close']
            portfolio_values.append(portfolio_value)
        return portfolio_values
        
    def calculate_sharpe_ratio(self, portfolio_values, risk_free_rate=0.01):
        daily_returns = [(portfolio_values[i] - portfolio_values[i-1]) / portfolio_values[i-1] 
                        for i in range(1, len(portfolio_values))]
        excess_returns = [r - risk_free_rate/252 for r in daily_returns]  # Assuming 252 trading days
        if len(excess_returns) > 0:
            sharpe_ratio = np.sqrt(252) * np.mean(excess_returns) / np.std(excess_returns)
            return sharpe_ratio
        else:
            return 0  # 또는 다른 적절한 기본값