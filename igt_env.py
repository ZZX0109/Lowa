"""
爱荷华赌博任务 (Iowa Gambling Task) 核心环境
供前端 Demo 与算法脚本共用，保证规则一致。
"""

import numpy as np


class IGTEnv:
    """
    IGT 规则引擎：无 UI，仅负责逻辑。
    牌堆 A/B 长期不利，C/D 长期有利。支持传入自定义 decks 覆盖默认。
    """

    DECK_NAMES = ('A', 'B', 'C', 'D')

    DEFAULT_DECKS = {
        'A': (100, 0.5, -250),
        'B': (100, 0.1, -1250),
        'C': (50, 0.5, -50),
        'D': (50, 0.1, -25),
    }

    def __init__(self, seed=None, decks=None):
        if seed is not None:
            np.random.seed(seed)
        # 每个牌堆: (每次收益, 罚款概率, 罚款金额)
        if decks is not None:
            self.decks = {k: (int(w), float(p), int(l)) for k, (w, p, l) in decks.items() if k in self.DECK_NAMES}
            for k in self.DECK_NAMES:
                if k not in self.decks:
                    self.decks[k] = self.DEFAULT_DECKS[k]
        else:
            self.decks = dict(self.DEFAULT_DECKS)
        self._balance = 0
        self._history = []  # [(choice, reward, balance_after), ...]

    def reset(self, initial_balance=2000):
        """重置环境与余额（算法训练时可用）。"""
        self._balance = initial_balance
        self._history = []
        return self._balance

    def step(self, choice):
        """
        执行一次选择，返回本次收益。
        choice: 'A' | 'B' | 'C' | 'D'
        returns: reward (int), 即本次 win + loss（loss 为 0 或负值）
        """
        if choice not in self.decks:
            raise ValueError(f"无效牌堆: {choice}，应为 A/B/C/D")
        win, p_loss, loss_val = self.decks[choice]
        loss = loss_val if np.random.random() < p_loss else 0
        reward = win + loss  # loss 为 0 或负数
        self._balance += reward
        self._history.append((choice, reward, self._balance))
        return reward

    @property
    def balance(self):
        return self._balance

    @property
    def history(self):
        return self._history.copy()

    def expected_reward(self, choice):
        """返回某牌堆的期望收益（用于分析与教学）。"""
        if choice not in self.decks:
            raise ValueError(f"无效牌堆: {choice}")
        win, p_loss, loss_val = self.decks[choice]
        return win + p_loss * loss_val
