import profile
from unittest import result
from urllib import request
from .models import Domain
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import Avg
import random
import csv

from .models import (
    Profile,
    Exam,
    Question,
    StudentAnswer,
    Result,
    DescriptiveAnswer,
    Domain,
)

# ---------------- AUTH ---------------- #

def signup(request):
    domains = Domain.objects.all()
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        role = request.POST['role']
        subject = request.POST.get('subject')

        if password != confirm_password:
            return render(request, 'exam/signup.html', {'error': 'Passwords do not match','domains': domains})

        if User.objects.filter(username=username).exists():
            return render(request, 'exam/signup.html', {'error': 'Username already exists','domains': domains})

        user = User.objects.create_user(username=username, email=email, password=password)
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.role = role
        if role == 'examiner' and not subject:
            return render(request, 'exam/signup.html', {
                'error': 'Subject is required for examiner',
                'domains': domains
            })
        profile.save()

        return redirect('login')
    return render(request, 'exam/signup.html', {
        'domains': domains
    })


def login_view(request):
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST['username'],
            password=request.POST['password']
        )

        if user:
            login(request, user)
            return redirect('dashboard')

    return render(request, 'exam/login.html')


# ---------------- DASHBOARDS ---------------- #

@login_required
def dashboard(request):

    # 🔥 HANDLE SUPERUSER (NO PROFILE REQUIRED)
    if request.user.is_superuser:
        return redirect('examiner_dashboard')

    # Normal users (must have profile)
    if hasattr(request.user, 'profile'):
        if request.user.profile.role == 'examiner':
            return redirect('examiner_dashboard')
        return redirect('student_dashboard')

    # Fallback (safety)
    return redirect('login')


@login_required
def examiner_dashboard(request):
    if not request.user.is_superuser:
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'examiner':
            return redirect('student_dashboard')

    profile = getattr(request.user, 'profile', None)

    results = Result.objects.select_related('user', 'exam', 'exam__domain')

    if profile and profile.subject:
        results = results.filter(
            exam__domain__name__iexact=profile.subject.replace("_", " ")
        )

    results = results.order_by('-submitted_at')

    # ✅ FIX TOTAL CALCULATION (DYNAMIC)
    for r in results:
        if r.exam.exam_type == 'DESCRIPTIVE':
            r.correct_total = r.exam.total_questions * 10
        else:
            r.correct_total = r.exam.total_questions

    return render(request, 'exam/examiner_dashboard.html', {
        'results': results
    })

@login_required
def create_exam(request):
    if not request.user.is_superuser:
        if request.user.profile.role != 'examiner':
            return redirect('student_dashboard')

    profile = getattr(request.user, 'profile', None)
    domains = Domain.objects.all()

    # Restrict domain for faculty
    if profile and profile.subject:
        domains = Domain.objects.filter(name__iexact=profile.subject.replace("_", " "))

    if request.method == 'POST':
        domain_id = request.POST.get('domain')
        exam_type = request.POST.get('exam_type')
        total_questions = int(request.POST.get('total_questions', 0))
        duration = int(request.POST.get('duration', 0))

        # ✅ BASIC VALIDATION
        if total_questions <= 0 or duration <= 0:
            return render(request, 'exam/create_exam.html', {
                'domains': domains,
                'error': 'Values must be positive'
            })

        # ✅ MCQ RULES
        if exam_type == 'MCQ':
            if total_questions > 100:
                return render(request, 'exam/create_exam.html', {
                    'domains': domains,
                    'error': 'MCQ cannot have more than 100 questions'
                })

            if duration != total_questions:
                return render(request, 'exam/create_exam.html', {
                    'domains': domains,
                    'error': f'MCQ duration must be equal to number of questions ({total_questions} minutes required)'
                })

        # ✅ DESCRIPTIVE RULES
        if exam_type == 'DESCRIPTIVE':
            if total_questions > 10:
                return render(request, 'exam/create_exam.html', {
                    'domains': domains,
                    'error': 'Descriptive exam cannot have more than 10 questions'
                })

            expected_duration = total_questions * 3

            if duration != expected_duration:
                return render(request, 'exam/create_exam.html', {
                    'domains': domains,
                    'error': f'Descriptive duration must be {expected_duration} minutes'
                })

        # 🔥 NEW FIX: CHECK AVAILABLE QUESTIONS IN DATABASE
        if exam_type == 'MCQ':
            available_questions = Question.objects.filter(
                domain_id=domain_id,
                question_type=Question.MCQ
            ).count()

        elif exam_type == 'DESCRIPTIVE':
            available_questions = Question.objects.filter(
                domain_id=domain_id,
                question_type=Question.DESCRIPTIVE
            ).count()

        if total_questions > available_questions:
            return render(request, 'exam/create_exam.html', {
                'domains': domains,
                'error': f'Only {available_questions} questions available in database for this domain'
            })

        domain = Domain.objects.get(id=domain_id)

        Exam.objects.create(
            domain=domain,
            exam_type=exam_type,
            total_questions=total_questions,
            duration=duration
        )

        return redirect('examiner_dashboard')

    return render(request, 'exam/create_exam.html', {
        'domains': domains
    })


@login_required
def student_dashboard(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'student':
        return redirect('examiner_dashboard')

    # ✅ GROUP EXAMS BY TYPE
    mcq_exams = Exam.objects.filter(exam_type=Exam.MCQ)
    descriptive_exams = Exam.objects.filter(exam_type=Exam.DESCRIPTIVE)
    attempted_exam_ids = Result.objects.filter(user=request.user).values_list('exam_id', flat=True)

    # ✅ Fetch student results
    results = Result.objects.filter(user=request.user).select_related('exam', 'exam__domain')

    # ✅ Prepare result dictionary (exam_id → result)
    result_map = {r.exam.id: r for r in results}

    return render(request, 'exam/student_dashboard.html', {
        'mcq_exams': mcq_exams,
        'descriptive_exams': descriptive_exams,
        'attempted_exam_ids': attempted_exam_ids,
        'result_map': result_map
    })


# ---------------- MCQ EXAM ---------------- #

@login_required
def start_exam(request, exam_id):
    exam = Exam.objects.get(id=exam_id)

    # ✅ BLOCK DESCRIPTIVE EXAM FROM MCQ FLOW
    if exam.exam_type == Exam.DESCRIPTIVE:
        return redirect('start_descriptive_exam', exam_id=exam.id)

    if Result.objects.filter(user=request.user, exam=exam).exists():
        return redirect('student_dashboard')

    if request.session.get('exam_in_progress') == exam_id:
        question_ids = request.session.get('question_ids', [])
        questions = Question.objects.filter(id__in=question_ids)
    else:
        # ✅ ONLY MCQ QUESTIONS
        all_questions = Question.objects.filter(
            domain=exam.domain,
            question_type=Question.MCQ
        )

        all_questions_list = list(all_questions)

        if len(all_questions_list) < exam.total_questions:
            return redirect('student_dashboard')  # or show error

        selected_questions = random.sample(all_questions_list, exam.total_questions)
        request.session['question_ids'] = [q.id for q in selected_questions]
        request.session['exam_in_progress'] = exam_id
        questions = selected_questions

    result, created = Result.objects.get_or_create(user=request.user, exam=exam)
    if created or result.started_at is None:
        result.started_at = timezone.now()
        result.save()

    return render(request, 'exam/exam_page.html', {
        'exam': exam,
        'questions': questions
    })


@login_required
def submit_exam(request, exam_id):
    exam = Exam.objects.get(id=exam_id)
    question_ids = request.session.get('question_ids', [])

    score = 0
    for qid in question_ids:
        question = Question.objects.get(id=qid)
        selected = request.POST.get(str(qid))

        if selected:
            selected = int(selected)
            is_correct = selected == question.correct_option
            if is_correct:
                score += 1

            StudentAnswer.objects.create(
                student=request.user,
                exam=exam,
                question=question,
                selected_option=selected,
                is_correct=is_correct
            )

    result = Result.objects.get(user=request.user, exam=exam)
    if result.started_at:
        result.duration_taken = int((timezone.now() - result.started_at).total_seconds())

    result.score = score
    result.total_questions = len(question_ids)
    result.save()

    request.session.pop('exam_in_progress', None)
    request.session.pop('question_ids', None)

    return render(request, 'exam/result.html', {
        'score': score,
        'total': len(question_ids),
        'exam': exam
    })


# ---------------- DESCRIPTIVE EXAM ---------------- #

@login_required
def start_descriptive_exam(request, exam_id):
    exam = Exam.objects.get(id=exam_id)

    # 🚫 Prevent MCQ exam from entering descriptive flow
    if exam.exam_type == Exam.MCQ:
        return redirect('start_exam', exam_id=exam.id)

    if Result.objects.filter(user=request.user, exam=exam).exists():
        return redirect('student_dashboard')

    # 🔵 Session lock (same as MCQ)
    request.session['exam_in_progress'] = exam_id  # 🔵 ADDED

    # 🔵 Fetch only descriptive questions
    questions = Question.objects.filter(
    domain=exam.domain,
    question_type=Question.DESCRIPTIVE
    )[:exam.total_questions]  # ✅ LIMIT APPLIED

    # 🔵 Store question IDs for consistency
    request.session['question_ids'] = [q.id for q in questions]  # 🔵 ADDED

    result, created = Result.objects.get_or_create(user=request.user, exam=exam)
    if created or result.started_at is None:
        result.started_at = timezone.now()
        result.save()

    return render(request, 'exam/descriptive_exam_page.html', {
        'exam': exam,
        'questions': questions
    })

@login_required
def submit_descriptive_exam(request, exam_id):
    exam = Exam.objects.get(id=exam_id)

    # ✅ ONLY FETCH REQUIRED NUMBER OF QUESTIONS
    questions = Question.objects.filter(
        domain=exam.domain,
        question_type=Question.DESCRIPTIVE
    )[:exam.total_questions]   # ⭐ CRITICAL FIX

    # ✅ DELETE OLD ANSWERS
    DescriptiveAnswer.objects.filter(
        student=request.user,
        exam=exam
    ).delete()

    for question in questions:
        DescriptiveAnswer.objects.create(
            student=request.user,
            exam=exam,
            question=question,
            answer_text=request.POST.get(f"question_{question.id}", "").strip()
        )

    result = Result.objects.get(user=request.user, exam=exam)

    if result.started_at:
        result.duration_taken = int((timezone.now() - result.started_at).total_seconds())

    # ✅ FIX TOTAL MARKS
    result.score = 0
    result.total_questions = exam.total_questions * 10   # correct total
    result.save()

    request.session.pop('exam_in_progress', None)
    request.session.pop('question_ids', None)

    return redirect('student_dashboard')



# ---------------- EXAMINER ---------------- #

@login_required
def examiner_results(request):
    if not request.user.is_superuser:
        if request.user.profile.role != 'examiner':
            return redirect('student_dashboard')

    results = Result.objects.select_related('user', 'exam').order_by('-submitted_at')
    return render(request, 'exam/examiner_results.html', {'results': results})


@login_required
def examiner_view_answers(request, result_id):

    if not request.user.is_superuser:
        if request.user.profile.role != 'examiner':
            return redirect('student_dashboard')

    result = Result.objects.select_related(
        'user',
        'exam',
        'exam__domain'
    ).get(id=result_id)

    # If exam is descriptive → go to evaluation page
    if result.exam.exam_type == Exam.DESCRIPTIVE:
        return redirect('evaluate_descriptive_exam', result_id=result.id)

    # Otherwise show MCQ answers
    answers = StudentAnswer.objects.select_related(
        'question'
    ).filter(
        student=result.user,
        exam=result.exam
    )

    return render(request, 'exam/examiner_view_answers.html', {
        'result': result,
        'answers': answers
    })


@login_required
def export_results_csv(request):
    if not request.user.is_superuser:
        if request.user.profile.role != 'examiner':
            return redirect('student_dashboard')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="exam_results.csv"'

    writer = csv.writer(response)
    writer.writerow(['Student', 'Exam Domain', 'Score', 'Total Questions', 'Submitted At'])

    results = Result.objects.select_related('user', 'exam', 'exam__domain').order_by('-submitted_at')
    for r in results:
        writer.writerow([
            r.user.username,
            r.exam.domain.name,
            r.score,
            r.total_questions,
            r.submitted_at.strftime("%Y-%m-%d %H:%M")
        ])

    return response


@login_required
def examiner_analytics(request):
    if not request.user.is_superuser:
        if request.user.profile.role != 'examiner':
            return redirect('student_dashboard')

    analytics = Result.objects.values('exam__domain__name').annotate(avg_score=Avg('score'))
    labels = [i['exam__domain__name'] for i in analytics]
    data = [round(i['avg_score'], 2) for i in analytics]

    return render(request, 'exam/examiner_analytics.html', {
        'labels': labels,
        'data': data
    })

# ---------------- DESCRIPTIVE EVALUATION (STEP 15) ---------------- #

@login_required
def examiner_descriptive_submissions(request):

    if not request.user.is_superuser:
        if request.user.profile.role != 'examiner':
            return redirect('student_dashboard')

    profile = getattr(request.user, 'profile', None)

    # Fetch descriptive exam results
    submissions = Result.objects.select_related(
        'user',
        'exam',
        'exam__domain'
    ).filter(
        exam__exam_type=Exam.DESCRIPTIVE
    )

    if profile and profile.subject:
        submissions = submissions.filter(
            exam__domain__name__iexact=profile.subject.replace("_", " ")
        )

    submissions = submissions.order_by('-submitted_at')

    # Convert submissions into submission_data for template
    submission_data = []

    for r in submissions:

        answers = DescriptiveAnswer.objects.filter(
            student=r.user,
            exam=r.exam
        )

        is_evaluated = answers.filter(evaluated=True).exists()

        submission_data.append({
            "result": r,
            "is_evaluated": is_evaluated
        })

    return render(
        request,
        'exam/examiner_descriptive_submissions.html',
        {
            'submission_data': submission_data
        }
    )



@login_required
def evaluate_descriptive_exam(request, result_id):
    if not request.user.is_superuser:
        if request.user.profile.role != 'examiner':
            return redirect('student_dashboard')

    result = Result.objects.select_related(
        'user', 'exam', 'exam__domain'
    ).get(id=result_id)

    answers = DescriptiveAnswer.objects.filter(
        exam=result.exam,
        student=result.user
    ).select_related('question')[:result.exam.total_questions]

    if request.method == 'POST':
        total_score = 0

        for answer in answers:
            marks = int(request.POST.get(f"marks_{answer.id}", 0))

            # ✅ STRICT LIMIT (0–10 per question)
            if marks < 0:
                marks = 0
            elif marks > 10:
                marks = 10

            answer.marks_awarded = marks
            answer.evaluated = True
            answer.save()

            total_score += marks

        # ✅ FINAL CORRECT CALCULATION
        result.score = total_score
        result.total_questions = result.exam.total_questions * 10   # ✅ ONLY ONCE
        result.save()

        return redirect('examiner_descriptive_submissions')

    return render(request, 'exam/evaluate_descriptive_exam.html', {
        'result': result,
        'answers': answers
    })

from django.http import JsonResponse

@login_required
def get_available_questions(request):
    domain_id = request.GET.get('domain_id')
    exam_type = request.GET.get('exam_type')

    if not domain_id or not exam_type:
        return JsonResponse({'count': 0})

    if exam_type == 'MCQ':
        count = Question.objects.filter(
            domain_id=domain_id,
            question_type=Question.MCQ
        ).count()
    elif exam_type == 'DESCRIPTIVE':
        count = Question.objects.filter(
            domain_id=domain_id,
            question_type=Question.DESCRIPTIVE
        ).count()
    else:
        count = 0

    return JsonResponse({'count': count})
