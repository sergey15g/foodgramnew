import base64
from io import BytesIO
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, AllowAny, IsAuthenticated
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from .serializers import UserSerializer, UserRegistrationSerializer, UserDetailSerializer, SetPasswordSerializer, SubscriptionSerializer
from .models import Subscription
from django.core.files.storage import default_storage

User = get_user_model()


class UserPagination(PageNumberPagination):
    page_size = 1
    page_size_query_param = 'limit'

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = UserPagination

    def get_serializer_class(self):
        if self.action == 'list':
            return UserSerializer
        if self.action == 'retrieve':
            return UserDetailSerializer
        if self.action == 'create':
            return UserRegistrationSerializer
        if self.action == 'set_password':
            return SetPasswordSerializer
        if self.action in ['avatar']:
            return UserDetailSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action == 'create':
            self.permission_classes = [AllowAny]
        else:
            self.permission_classes = [IsAuthenticatedOrReadOnly]
        if self.action in ['set_password', 'avatar']:
            self.permission_classes = [IsAuthenticated]
        return super(UserViewSet, self).get_permissions()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            response_data = UserRegistrationSerializer(user).data
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticatedOrReadOnly], url_path='me')
    def me(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return Response({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = UserDetailSerializer(user, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated], url_path='set_password')
    def set_password(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['put', 'delete'], permission_classes=[IsAuthenticated], url_path='me/avatar')
    def avatar(self, request, *args, **kwargs):
        user = request.user

        if request.method == 'PUT' or request.method == 'PATCH':
            # Check if avatar is provided in base64 format
            avatar_base64 = request.data.get('avatar')
            if avatar_base64:
                try:
                    # Decode base64 string
                    format, imgstr = avatar_base64.split(';base64,')
                    ext = format.split('/')[-1]
                    data = base64.b64decode(imgstr)
                    # Create a file-like object for Django
                    file_name = f"{user.id}_avatar.{ext}"
                    file = ContentFile(data, file_name)
                    user.avatar = file
                    user.save()
                    return Response(
                        {'avatar': user.avatar.url},
                        status=status.HTTP_200_OK
                    )
                except Exception as e:
                    return Response(
                        {'detail': 'Invalid base64 data.', 'error': str(e)},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            return Response(
                {'detail': 'No avatar provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        elif request.method == 'DELETE':
            if user.avatar:
                if default_storage.exists(user.avatar.name):
                    default_storage.delete(user.avatar.name)
                user.avatar = ''  # Set to empty string instead of None
                user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated], url_path='subscribe')
    def subscribe(self, request, pk=None):
        subscriber = request.user
        target_user = self.get_object()

        if subscriber == target_user:
            return Response({"detail": "You cannot subscribe to yourself."}, status=status.HTTP_400_BAD_REQUEST)

        subscription, created = Subscription.objects.get_or_create(user=subscriber, subscribed_to=target_user)

        if created:
            serializer = SubscriptionSerializer(subscription)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response({"detail": "Already subscribed."}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='subscriptions')
    def subscriptions(self, request, *args, **kwargs):
        user = request.user
        subscriptions = Subscription.objects.filter(user=user)
        
        # Применение пагинации
        page = self.paginate_queryset(subscriptions)
        if page is not None:
            serializer = SubscriptionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = SubscriptionSerializer(subscriptions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)