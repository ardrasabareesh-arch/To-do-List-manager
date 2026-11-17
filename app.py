
from flask import Flask, render_template, request, redirect, url_for
import json
import os
from datetime import datetime, date

app = Flask(__name__)

FILE = "tasks.json"
DELETED_FILE = "deleted_tasks.json"


def load_data(filename):
    if os.path.exists(filename):
        try:
            with open(filename, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []
    return []


tasks = load_data(FILE)
deleted_tasks = load_data(DELETED_FILE)


def save_tasks():
    with open(FILE, "w") as f:
        json.dump(tasks, f, indent=4)


def save_deleted():
    with open(DELETED_FILE, "w") as f:
        json.dump(deleted_tasks, f, indent=4)


def get_deadline_status(task):
    deadline = datetime.strptime(
        task["deadline"], "%Y-%m-%d"
    ).date()

    if task["status"] == "Completed":
        return "Completed"
    elif deadline < date.today():
        return "Overdue"
    elif (deadline - date.today()).days <= 7:
        return "Upcoming"
    return "On Track"


@app.route("/")
def index():
    search = request.args.get("search", "").lower()
    priority = request.args.get("priority", "All")
    view = request.args.get("view", "all")

    if view == "deleted":
        source = deleted_tasks
    elif view == "completed":
        source = [t for t in tasks if t["status"] == "Completed"]
    elif view == "pending":
        source = [t for t in tasks if t["status"] == "Pending"]
    else:
        source = tasks

    filtered_tasks = []

    for task in source:
        if search not in task["name"].lower():
            continue
        if priority != "All" and task["priority"] != priority:
            continue
        filtered_tasks.append(task)

    total = len(tasks)
    completed = sum(t["status"] == "Completed" for t in tasks)
    pending = sum(t["status"] == "Pending" for t in tasks)
    overdue = sum(
        get_deadline_status(t) == "Overdue" for t in tasks
    )

    rate = round(completed / total * 100) if total else 0

    return render_template(
        "index.html",
        tasks=filtered_tasks,
        total=total,
        completed=completed,
        pending=pending,
        overdue=overdue,
        rate=rate,
        deleted_count=len(deleted_tasks),
        get_deadline_status=get_deadline_status,
        search=search,
        selected_priority=priority,
        view=view,
        edit_task=None
    )


@app.route("/add", methods=["POST"])
def add_task():
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    priority = request.form.get("priority")
    deadline = request.form.get("deadline")

    if not name or priority not in ["High", "Medium", "Low"]:
        return redirect(url_for("index"))

    try:
        datetime.strptime(deadline, "%Y-%m-%d")
    except (ValueError, TypeError):
        return redirect(url_for("index"))

    all_ids = [t["id"] for t in tasks + deleted_tasks]

    task = {
        "id": max(all_ids, default=0) + 1,
        "name": name,
        "description": description,
        "priority": priority,
        "deadline": deadline,
        "status": "Pending"
    }

    tasks.append(task)
    save_tasks()

    return redirect(url_for("index"))


@app.route("/complete/<int:task_id>", methods=["POST"])
def complete_task(task_id):
    for task in tasks:
        if task["id"] == task_id:
            task["status"] = "Completed"
            break

    save_tasks()
    return redirect(url_for("index"))


@app.route("/delete/<int:task_id>", methods=["POST"])
def delete_task(task_id):
    for task in tasks:
        if task["id"] == task_id:
            deleted_tasks.append(task)
            tasks.remove(task)
            break

    save_tasks()
    save_deleted()

    return redirect(url_for("index"))


@app.route("/restore/<int:task_id>", methods=["POST"])
def restore_task(task_id):
    for task in deleted_tasks:
        if task["id"] == task_id:
            tasks.append(task)
            deleted_tasks.remove(task)
            break

    save_tasks()
    save_deleted()

    return redirect(url_for("index", view="deleted"))


@app.route("/permanent-delete/<int:task_id>", methods=["POST"])
def permanent_delete(task_id):
    global deleted_tasks

    deleted_tasks = [
        t for t in deleted_tasks if t["id"] != task_id
    ]

    save_deleted()
    return redirect(url_for("index", view="deleted"))


@app.route("/edit/<int:task_id>", methods=["GET", "POST"])
def edit_task(task_id):
    task = next((t for t in tasks if t["id"] == task_id), None)

    if task is None:
        return redirect(url_for("index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        priority = request.form.get("priority")
        deadline = request.form.get("deadline")

        try:
            datetime.strptime(deadline, "%Y-%m-%d")
        except (ValueError, TypeError):
            return redirect(url_for("index"))

        if name and priority in ["High", "Medium", "Low"]:
            task["name"] = name
            task["description"] = description
            task["priority"] = priority
            task["deadline"] = deadline

            save_tasks()
            return redirect(url_for("index"))

    return render_template(
        "index.html",
        tasks=tasks,
        total=len(tasks),
        completed=sum(t["status"] == "Completed" for t in tasks),
        pending=sum(t["status"] == "Pending" for t in tasks),
        overdue=sum(get_deadline_status(t) == "Overdue" for t in tasks),
        rate=round(
            sum(t["status"] == "Completed" for t in tasks)
            / len(tasks) * 100
        ) if tasks else 0,
        deleted_count=len(deleted_tasks),
        get_deadline_status=get_deadline_status,
        search="",
        selected_priority="All",
        view="all",
        edit_task=task
    )


if __name__ == "__main__":
    app.run(debug=True)

