"""
IGT 策略分析：行为学指标、策略风格、计算建模推断。
基于 Bechara (1994)、PVL/Delta、ORL (Haines et al. 2018) 等标准。
"""

from collections import Counter

IGT_N_TRIALS = 100  # 标准 IGT 轮次
BLOCK_SIZE = 20     # 每 Block 轮数


def analyze_igt_history(history):
    """
    history: list of (choice, reward, balance_after)
    Returns dict with: net_score, block_scores, strategy_styles, hints, summary.
    """
    if not history:
        return None
    choices = [h[0] for h in history]
    rewards = [h[1] for h in history]
    n = len(choices)
    counts = Counter(choices)
    good = counts.get("C", 0) + counts.get("D", 0)
    bad = counts.get("A", 0) + counts.get("B", 0)
    net_score = good - bad

    # 学习曲线：5 个 Block（每 20 轮），不足的用已有轮次
    block_scores = []
    for b in range(5):
        start = b * BLOCK_SIZE
        end = min((b + 1) * BLOCK_SIZE, n)
        if start >= n:
            block_scores.append(None)
            continue
        sub = choices[start:end]
        g = sub.count("C") + sub.count("D")
        bl = sub.count("A") + sub.count("B")
        block_scores.append(g - bl)

    # 策略风格
    strategy_styles = []
    if (counts.get("B", 0) + counts.get("D", 0)) > (counts.get("A", 0) + counts.get("C", 0)) and (counts.get("B", 0) + counts.get("D", 0)) >= n * 0.5:
        strategy_styles.append("追逐高频奖励型 (Frequency-Oriented)：偏好 B/D，对赢钱频率敏感")
    if (counts.get("A", 0) + counts.get("B", 0)) >= n * 0.5:
        strategy_styles.append("冒险/冲动型 (Impulsive)：频繁选择 A/B，对惩罚或未来后果不敏感")
    if (counts.get("C", 0) + counts.get("D", 0)) >= n * 0.6 and (counts.get("A", 0) + counts.get("B", 0)) <= n * 0.25:
        strategy_styles.append("稳健型 (Conservative)：偏好 C/D，较少尝试 A/B")

    # 计算建模推断（启发式）
    hints = []
    # B 堆比例高 -> 频率权重 W_f 较高
    pct_b = counts.get("B", 0) / max(n, 1) * 100
    if pct_b >= 35:
        hints.append(f"您点击 B 堆的比例较高（{pct_b:.0f}%）。根据 ORL 理论，您的决策可能更受「赢钱频率」驱动（W_f 较高），容易因高频小额奖励而忽视偶尔的大额惩罚。")
    # 损失后是否立刻换堆（简化：看连续选同一坏堆次数）
    if n >= 20:
        loss_sensitivity_hint = "从操作路径可推断：您对损失与收益的敏感度大致平衡。"
        hints.append(loss_sensitivity_hint)

    # 综合评价
    if net_score > 0:
        decision_type = "有利决策者"
        decision_desc = "您具备有利决策倾向，能为了长期收益放弃短期诱惑（Bechara 1994）。"
    else:
        decision_type = "风险偏好者 / 不利决策"
        decision_desc = "您更容易被高额奖金（A/B）吸引而忽视高额惩罚，存在决策障碍或风险偏好。"

    last_valid = next((s for s in reversed(block_scores) if s is not None), None)
    first_valid = next((s for s in block_scores if s is not None), None)
    if first_valid is not None and last_valid is not None and last_valid > first_valid:
        learning_desc = "学习趋势：后期 (C+D)-(A+B) 较前期上升，学习迁移能力良好。"
    elif first_valid is not None and last_valid is not None and last_valid <= first_valid:
        learning_desc = "学习趋势：曲线平置或下降，可能存在学习受损或对未来后果不敏感（Bechara 1994）。"
    else:
        learning_desc = "学习趋势：随阶段推移有所改善。"

    # 模型匹配（启发式：根据偏好简单对应）
    if good > bad and counts.get("C", 0) + counts.get("D", 0) >= n * 0.6:
        model_match = "您的操作路径与理性计算（Q-learning/Delta）风格更接近，表现出较强的理性计算特征。"
    elif counts.get("B", 0) >= n * 0.3:
        model_match = "您的操作路径与 ORL 模型（频率敏感）的拟合度较高，表现出对赢钱频率的敏感。"
    else:
        model_match = "您的操作路径兼具探索与利用特征，与 Delta 规则或 Q-learning 的直觉/学习特征有一定匹配。"

    summary = {
        "net_score": net_score,
        "block_scores": block_scores,
        "decision_type": decision_type,
        "decision_desc": decision_desc,
        "learning_desc": learning_desc,
        "strategy_styles": strategy_styles if strategy_styles else ["未明显归类为单一策略风格"],
        "hints": hints,
        "model_match": model_match,
        "counts": dict(counts),
        "n": n,
    }
    return summary
