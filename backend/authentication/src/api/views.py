# api/v1/auth/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django.contrib.auth.models import User
from django.middleware.csrf import get_token
from .serializers import UserSerializer
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user(request):
    """
    Get the current authenticated user's details
    """
    user = request.user
    serializer = UserSerializer(user)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def user_list(request):
    """
    Get a list of users - only accessible by admin users
    """
    # Get most recent users first
    users = User.objects.all().order_by('-date_joined')

    # Convert to list of dictionaries for the response
    user_data = []
    for user in users:
        user_data.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'date_joined': user.date_joined,
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'last_login': user.last_login,
            'name': user.get_full_name() or user.username
        })

    return Response(user_data)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Handle user login
    """
    username = request.data.get('username')
    password = request.data.get('password')

    # Try to authenticate with username first
    user = authenticate(username=username, password=password)

    # If authentication with username fails, try with email
    if user is None:
        try:
            user = User.objects.get(email=username)
            user = authenticate(username=user.username, password=password)
        except User.DoesNotExist:
            user = None

    if user is not None:
        django_login(request, user)
        token, created = Token.objects.get_or_create(user=user)

        return Response({
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.get_full_name() or user.username,
                'isAdmin': user.is_staff or user.is_superuser
            },
            'token': token.key
        }, status=status.HTTP_200_OK)

    return Response(
        {'error': 'Invalid username/email or password'},
        status=status.HTTP_401_UNAUTHORIZED
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Handle new user registration (updated to match frontend expectations)
    """
    email = request.data.get('email')
    password = request.data.get('password')
    name = request.data.get('name', '')  # Optional name field

    # Generate username from email if not provided
    username = request.data.get('username') or email.split('@')[0]

    # Validate required fields
    if not email or not password:
        return Response(
            {'error': 'Email and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate email format
    try:
        validate_email(email)
    except ValidationError:
        return Response(
            {'error': 'Enter a valid email address'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check if email already exists
    if User.objects.filter(email=email).exists():
        return Response(
            {'error': 'Email already registered'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Generate unique username if the default one exists
    if User.objects.filter(username=username).exists():
        username = f"{username}_{User.objects.count() + 1}"

    try:
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=name
        )

        # Create auth token
        token = Token.objects.create(user=user)

        # Return data in format expected by frontend
        return Response({
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.get_full_name() or username,
                'isAdmin': False  # Matches frontend expectation
            },
            'token': token.key
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    Handle user logout
    """
    try:
        # Delete the token if using token authentication
        Token.objects.filter(user=request.user).delete()
        django_logout(request)
        return Response(
            {'message': 'Successfully logged out'},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_csrf_token(request):
    """
    Get CSRF token for session authentication
    """
    return Response({'csrf_token': get_token(request)})