# 爱荷华赌博任务 · 教学 Demo

行为经济学实验：前端体验 + 同一套环境供算法训练。

## 结构

- **`app.py`**：**统一入口**。运行后先选择进入四个实验室之一（两行两列）：自己玩 / Delta / Q-learning / ORL；整体风格 skyblue。
- **`.streamlit/config.toml`**：主题配置（skyblue 色系）。
- **`pages/`**：四个实验室页面（1_自己玩、2_Delta算法、3_Qlearning、4_ORL算法）。
- **`igt_env.py`**：核心规则引擎，无 UI，前端与算法共用。
- **`demo.py`**：单独的人玩前端（也可用入口进入「自己玩」）。
- **`run_delta.py`** / **`run_qlearning.py`** / **`run_orl.py`**：Delta / Q-learning / ORL 智能体，可前端运行或 **`--auto`** 自动化跑 IGT。
- **`run_agents.py`**：终端一次性跑两种算法并弹出 matplotlib 对比图（可选）。

## 使用

### 0. 统一入口（推荐）

```bash
streamlit run app.py
```

在初始界面选择（两行两列）：**自己玩** / **Delta 规则** / **Q-learning** / **ORL 模型** 进入对应实验室；侧栏也可切换页面。整体风格为 skyblue（由 `.streamlit/config.toml` 配置）。

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 前端体验（学生自己玩）

```bash
streamlit run demo.py
```

在浏览器中打开提示的地址，点击牌堆 A/B/C/D，观察余额与奖惩。

### 3. Delta 规则 · 前端逐步看日志与路径

```bash
streamlit run run_delta.py
```

在侧栏设置轮数、学习率、温度、每步延迟等，点击「开始运行 Delta 规则」，即可在前端**逐步**看到：当前余额、运行日志（含 V 值）、选择路径表、余额曲线，与人玩时看到的路径形式一致。

### 4. Q-learning · 前端逐步看日志与路径

```bash
streamlit run run_qlearning.py
```

同样在侧栏设置参数后点击「开始运行 Q-learning」，在前端逐步看到：当前余额、运行日志（含 Q 值与探索/利用）、选择路径表、余额曲线。

### 5. Delta / Q-learning / ORL · 自动化跑（与 demo 同一环境）

在终端自动跑完，不打开浏览器，用与 `demo.py` 相同的 `igt_env`：

```bash
python run_delta.py --auto
python run_qlearning.py --auto
python run_orl.py --auto
```

可选参数示例：

```bash
python run_delta.py --auto --trials 500 --alpha 0.15 --temp 1.5 --seed 42 --log-every 100
python run_qlearning.py --auto -n 500 --alpha 0.15 --epsilon 0.1 --seed 42 --log-every 100
python run_orl.py --auto -n 500 --alpha-v 0.15 --alpha-f 0.15 --W-v 0.5 --W-f 0.5 --log-every 100
```

（`-n` 即 `--trials`，`-a` 即 `--auto`。）

### 6. 算法对比（终端一次性跑两种）

```bash
python run_agents.py
```

会跑 20 次 × 1000 轮，并弹出 matplotlib 对比图（Delta 规则 vs Q-learning）。

## 牌堆说明

| 牌堆 | 每次收益 | 罚款概率 | 罚款额 | 期望/次 |
|------|----------|----------|--------|---------|
| A    | +100     | 50%      | -250   | ≈ -25   |
| B    | +100     | 10%      | -1250  | ≈ -25   |
| C    | +50      | 50%      | -50    | ≈ +25   |
| D    | +50      | 10%      | -25    | ≈ +47.5 |

理性策略应多选 C、D；人类常被 A、B 的高收益吸引而偏向不利牌堆。
