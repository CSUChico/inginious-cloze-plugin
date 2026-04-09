(function () {
    "use strict";

    function normalizeText(node) {
        return (node && node.textContent ? node.textContent : "").replace(/\s+/g, " ").trim();
    }

    function extractFeedbackText() {
        var alerts = document.querySelectorAll(".alert");
        for (var i = 0; i < alerts.length; i += 1) {
            var text = normalizeText(alerts[i]);
            if (text.indexOf("Your score is ") !== -1 || text.indexOf("Your submission timed out.") !== -1) {
                return text;
            }
        }
        return "";
    }

    function inferStatus(text) {
        if (!text) {
            return null;
        }
        if (text.indexOf("Your answer passed the tests!") !== -1) {
            return "Succeeded";
        }
        if (
            text.indexOf("There are some errors in your answer.") !== -1 ||
            text.indexOf("Your submission timed out.") !== -1 ||
            text.indexOf("Your submission made an overflow.") !== -1 ||
            text.indexOf("Your submission was killed.") !== -1
        ) {
            return "Failed";
        }
        return null;
    }

    function inferGrade(text) {
        var match = text.match(/Your score is ([0-9]+(?:\.[0-9]+)?)%/);
        return match ? match[1] : null;
    }

    function syncSidebarFromFeedback() {
        var feedbackText = extractFeedbackText();
        if (!feedbackText) {
            return;
        }

        var status = inferStatus(feedbackText);
        var grade = inferGrade(feedbackText);

        var statusNode = document.getElementById("task_status");
        if (statusNode && status) {
            statusNode.textContent = status;
        }

        var gradeNode = document.getElementById("task_grade");
        if (gradeNode && grade !== null) {
            gradeNode.textContent = grade;
        }
    }

    function init() {
        syncSidebarFromFeedback();

        var observer = new MutationObserver(function () {
            syncSidebarFromFeedback();
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true,
            characterData: true
        });

        var taskForm = document.getElementById("task");
        if (taskForm) {
            taskForm.addEventListener("submit", function () {
                window.setTimeout(syncSidebarFromFeedback, 250);
                window.setTimeout(syncSidebarFromFeedback, 1000);
                window.setTimeout(syncSidebarFromFeedback, 2500);
            });
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
