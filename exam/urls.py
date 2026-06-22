from django import views
from django.urls import path
from .views import *
from . import views

urlpatterns = [
    path('', login_view, name='login'),
    path('signup/', signup, name='signup'),
    path('dashboard/', dashboard, name='dashboard'),
    path('examiner/', examiner_dashboard, name='examiner_dashboard'),
    path('student/', student_dashboard, name='student_dashboard'),
    path('start-exam/<int:exam_id>/', start_exam, name='start_exam'),
    path('start-descriptive-exam/<int:exam_id>/', start_descriptive_exam, name='start_descriptive_exam'),
    path('submit-exam/<int:exam_id>/', submit_exam, name='submit_exam'),
    path('submit-descriptive-exam/<int:exam_id>/', submit_descriptive_exam, name='submit_descriptive_exam'),
    path('examiner/descriptive-submissions/', examiner_descriptive_submissions, name='examiner_descriptive_submissions'),
    path('examiner/evaluate-descriptive/<int:result_id>/', evaluate_descriptive_exam, name='evaluate_descriptive_exam'),
    path('examiner/results/', examiner_results, name='examiner_results'),
    path('examiner/result/<int:result_id>/', examiner_view_answers, name='examiner_view_answers'),
    path('examiner/export-results/', export_results_csv, name='export_results_csv'),
    path('examiner/analytics/', examiner_analytics, name='examiner_analytics'),
    path('create-exam/', views.create_exam, name='create_exam'),
    path('get-questions-count/', views.get_available_questions, name='get_questions_count'),
]
