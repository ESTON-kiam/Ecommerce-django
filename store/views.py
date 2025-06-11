from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from .models import Product, Category, Cart, CartItem, Order, OrderItem
from .forms import CustomUserCreationForm, CheckoutForm

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

def home(request):
    products = Product.objects.all().order_by('-created_at')
    categories = Category.objects.all()
    
    # Search functionality
    query = request.GET.get('q')
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
    
    # Category filter
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)
    
    context = {
        'products': products,
        'categories': categories,
        'query': query,
    }
    return render(request, 'store/home.html', context)

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'store/product_detail.html', {'product': product})

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart, 
        product=product,
        defaults={'quantity': 1}
    )
    
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    
    # Check if total quantity in cart exceeds available stock
    if cart_item.quantity > product.stock:
        messages.error(request, f'Only {product.stock} units of {product.name} available!')
        cart_item.quantity = product.stock
        cart_item.save()
    else:
        messages.success(request, f'{product.name} added to cart!')
    
    return redirect('product_detail', pk=product_id)

@login_required
def cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    return render(request, 'store/cart.html', {'cart': cart})

@login_required
def update_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'increase':
            cart_item.quantity += 1
            cart_item.save()
        elif action == 'decrease' and cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        elif action == 'remove':
            cart_item.delete()
    
    return redirect('cart')

@login_required
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)
    
    if not cart.items.exists():
        messages.warning(request, 'Your cart is empty!')
        return redirect('cart')
    
    # Check stock availability before checkout
    for cart_item in cart.items.all():
        if cart_item.quantity > cart_item.product.stock:
            messages.error(request, f'Only {cart_item.product.stock} units of {cart_item.product.name} available!')
            return redirect('cart')
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Double-check stock before creating order
            for cart_item in cart.items.all():
                if cart_item.quantity > cart_item.product.stock:
                    messages.error(request, f'Not enough stock for {cart_item.product.name}!')
                    return redirect('cart')
            
            order = form.save(commit=False)
            order.user = request.user
            order.total_amount = cart.total_amount
            order.save()
            
            # Create order items and decrease stock
            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    price=cart_item.product.discounted_price
                )
                
                # Decrease stock
                cart_item.product.stock -= cart_item.quantity
                cart_item.product.save()
            
            # Clear cart
            cart.items.all().delete()
            
            messages.success(request, f'Order placed successfully! Order ID: {order.order_id}')
            return redirect('order_tracking')
    else:
        form = CheckoutForm()
    
    return render(request, 'store/checkout.html', {'form': form, 'cart': cart})

@login_required
def order_tracking(request):
    orders = Order.objects.filter(user=request.user)
    
    # Track specific order
    order_id = request.GET.get('order_id')
    specific_order = None
    if order_id:
        try:
            specific_order = Order.objects.get(order_id=order_id, user=request.user)
        except Order.DoesNotExist:
            messages.error(request, 'Order not found!')
    
    context = {
        'orders': orders,
        'specific_order': specific_order,
    }
    return render(request, 'store/order_tracking.html', context)

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})




@csrf_protect
@never_cache
def login_view(request):
    """
    Handle user login
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            
            login(request, user)
           
            return redirect('home')  
        else:
           
            messages.error(request, 'Invalid username or password. Please try again.')
    
    return render(request, 'registration/login.html')


def logout_view(request):
    """
    Handle user logout and redirect to home
    """
    logout(request)  
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')  




