from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Domain(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Question(models.Model):
    MCQ = 'MCQ'
    DESCRIPTIVE = 'DESCRIPTIVE'

    QUESTION_TYPES = [
        (MCQ, 'Multiple Choice'),
        (DESCRIPTIVE, 'Descriptive'),
    ]

    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    question_text = models.TextField()

    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPES,
        default=MCQ
    )

    option1 = models.CharField(max_length=255, blank=True, null=True)
    option2 = models.CharField(max_length=255, blank=True, null=True)
    option3 = models.CharField(max_length=255, blank=True, null=True)
    option4 = models.CharField(max_length=255, blank=True, null=True)
    correct_option = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return self.question_text[:50]
    
class Exam(models.Model):
    MCQ = 'MCQ'
    DESCRIPTIVE = 'DESCRIPTIVE'

    EXAM_TYPES = [
        (MCQ, 'MCQ'),
        (DESCRIPTIVE, 'Descriptive'),
    ]

    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    total_questions = models.IntegerField()
    duration = models.IntegerField(help_text="Duration in minutes")

    exam_type = models.CharField(
        max_length=20,
        choices=EXAM_TYPES,
        default=MCQ
    )

    def __str__(self):
        return f"{self.domain.name} ({self.exam_type})"


class DescriptiveAnswer(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    # attempt_id = models.IntegerField(default=1)
    result = models.ForeignKey('Result',on_delete=models.SET_NULL,null=True,blank=True,related_name='descriptive_answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer_text = models.TextField()
    marks_awarded = models.IntegerField(null=True, blank=True)
    evaluated = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.question.id}"

from django.utils import timezone

class Result(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    total_questions = models.IntegerField(default=0)
    score = models.IntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    duration_taken = models.IntegerField(help_text="Duration in seconds", default=0)

    def __str__(self):
        return f"{self.user.username} - {self.exam.domain.name}"


from django.contrib.auth.models import User

class Profile(models.Model):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('examiner', 'Examiner'),
    )
    SUBJECT_CHOICES = (
        ('computer_networks', 'Computer Networks'),
        ('cyber_security', 'Cyber Security'),
        ('dbms', 'DBMS'),
        ('java', 'Java'),
        ('python', 'Python'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    subject = models.CharField(
        max_length=50,
        choices=SUBJECT_CHOICES,
        null=True,
        blank=True
    )
    def __str__(self):
        return self.user.username

class StudentAnswer(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.IntegerField()
    is_correct = models.BooleanField()
    answered_at = models.DateTimeField(auto_now_add=True)

# from django.db.models.signals import post_save
# from django.dispatch import receiver

# @receiver(post_save, sender=User)
# def create_user_profile(sender, instance, created, **kwargs):
#     if created:
#         Profile.objects.create(user=instance)

# @receiver(post_save, sender=User)
# def save_user_profile(sender, instance, **kwargs):
#     Profile.objects.get_or_create(user=instance)