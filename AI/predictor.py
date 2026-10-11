from sklearn.linear_model import LinearRegression


def calculate_academic_risk(
    attendance_percentage,
    quiz_percentage
):

    academic_score = (
        attendance_percentage * 0.40
        + quiz_percentage * 0.60
    )

    if (
        attendance_percentage < 60
        or quiz_percentage < 40
    ):

        risk_level = "High Risk"

        message = (
            "Your attendance or quiz performance "
            "needs immediate attention."
        )

        recommendation = (
            "Attend classes regularly and practice "
            "the weak topics using AI Tutor and Smart Quiz."
        )

    elif (
        attendance_percentage < 75
        or quiz_percentage < 60
    ):

        risk_level = "Moderate Risk"

        message = (
            "Your academic performance is moderate. "
            "There are areas that can be improved."
        )

        recommendation = (
            "Improve attendance and practice the topics "
            "where your quiz scores are lower."
        )

    else:

        risk_level = "Low Risk"

        message = (
            "Your current academic indicators are "
            "within a good range."
        )

        recommendation = (
            "Maintain your attendance and continue "
            "regular quiz practice."
        )

    return {
        "academic_score": academic_score,
        "risk_level": risk_level,
        "message": message,
        "recommendation": recommendation
    }


def predict_next_score(quiz_results):

    """
    Predict the student's next quiz percentage
    using the trend of previous quiz scores.
    """

    if not quiz_results:

        return None, "No quiz data available."

    # Extract previous percentages
    scores = [
        float(row[4])
        for row in quiz_results
    ]

    # With only one quiz, ML cannot learn a trend
    if len(scores) < 2:

        return (
            scores[0],
            "Complete at least one more quiz "
            "to improve prediction accuracy."
        )

    # Quiz sequence: 1, 2, 3, ...
    X = [
        [i]
        for i in range(1, len(scores) + 1)
    ]

    y = scores

    # Create and train model
    model = LinearRegression()

    model.fit(X, y)

    # Predict next quiz
    next_quiz_number = len(scores) + 1

    predicted_score = model.predict(
        [[next_quiz_number]]
    )[0]

    # Keep prediction between 0 and 100
    predicted_score = max(
        0,
        min(100, predicted_score)
    )

    # Determine trend
    if len(scores) >= 2:

        difference = scores[-1] - scores[0]

        if difference > 5:

            trend = "Improving 📈"

        elif difference < -5:

            trend = "Declining 📉"

        else:

            trend = "Stable ➡️"

    else:

        trend = "Stable ➡️"

    return predicted_score, trend