from django.http import JsonResponse
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from django.contrib.auth.models import User
from django.contrib import messages
from django.core.paginator import Paginator

from django.conf import settings

from django.db.models import Q # queryset
from . forms import CheckoutForm, CustomerRegister
from . models import *

from django.contrib.auth import login, logout, authenticate

from django.contrib.auth.decorators import login_required

# Create your views here.

# all products
def index(request):
    allproduct = Product.objects.all().order_by('-created_at') # minus (-) means descending order
    allcategory = Category.objects.all()
    # paginator
    p = Paginator(allproduct, 4)
    page_number = request.GET.get('page')
    product_list = p.get_page(page_number)
    
    context = {
        'show':allproduct,
        'category':allcategory,
        'paginators': product_list
    }
    return render(request,'stores/index.html',context)

# all category
def category(request):
    allcategory = Category.objects.all()
    context = {
        'category':allcategory
    }
    return render(request, 'stores/category.html',context)

# single product
def singleproduct(request,slug):
    singleproduct = Product.objects.get(slug=slug)
    singleproduct.view_count += 1
    singleproduct.save()
    context = {
        'show':singleproduct,
    }    
    return render(request, 'stores/single-product.html',context)

# add product to cart
def addtocart(request,id):
    cart_product = Product.objects.get(id=id)
#   check if cart exist
    cart_id = request.session.get('cart_id', None)
    if cart_id:
        cart_item = Cart.objects.get(id=cart_id)
        this_product_in_cart = cart_item.cartproduct_set.filter(product=cart_product)
        # assign cart to customer
        if request.user.is_authenticated and request.user.customer:
            cart_item.customer = request.user.customer
            cart_item.save()
        # end
        # checking if item exists in cart
        if this_product_in_cart.exists():
            cartproduct = this_product_in_cart.last()
            cartproduct.quantity += 1
            cartproduct.subtotal += cart_product.price
            cartproduct.save()
            cart_item.total += cart_product.price
            cart_item.save()
            messages.success(request, 'item increased in cart')

        # new item in cart
        else:
            cartproduct = CartProduct.objects.create(
            cart=cart_item, product=cart_product, rate=cart_product.price, quantity=1, subtotal=cart_product.price)
            cart_item.total += cart_product.price
            cart_item.save()
            messages.success(request, 'item added to cart')            
    else:
        cart_item = Cart.objects.create(total=0)
        request.session['cart_id'] = cart_item.id
        cartproduct = CartProduct.objects.create(cart=cart_item, 
        product=cart_product, 
        rate = cart_product.price, 
        quantity=1, 
        subtotal=cart_product.price)
        cart_item.total += cart_product.price
        cart_item.save()
        messages.success(request, 'New item added to cart')
    return redirect('index')

# my cart
def myCart(request):
    cart_id = request.session.get('cart_id', None)
    if cart_id:
        cart = Cart.objects.get(id=cart_id)
        # assign cart to customer
        if request.user.is_authenticated and request.user.customer:
            cart.customer = request.user.customer
            cart.save()
        # end        
    else:
        cart = None
    context = {
        'cart':cart,
    }
    return render(request, 'stores/mycart.html', context)

# manage cart
def manageCart(request,id):

    action = request.GET.get('action')
    cart_obj = CartProduct.objects.get(id=id)
    cart = cart_obj.cart

    if action == 'inc':
        cart_obj.quantity += 1
        cart_obj.subtotal += cart_obj.rate
        cart_obj.save()
        cart.total += cart_obj.rate
        cart.save()
        messages.success(request, 'item quantity increased in cart')                       
    elif action == 'dcr':
        cart_obj.quantity -= 1
        cart_obj.subtotal -= cart_obj.rate
        cart_obj.save()
        cart.total -= cart_obj.rate
        cart.save()
        messages.success(request, 'item quantity decreased in cart')        
        if cart_obj.quantity == 0:
            cart_obj.delete()
    elif action == 'rmv':
        cart.total -= cart_obj.subtotal
        cart.save 
        cart_obj.delete()
        messages.success(request, 'item removed from cart')          
    else:
        pass

    return redirect('myCart')

def emptyCart(request):
    cart_id = request.session.get('cart_id', None)
    if cart_id:
        cart = Cart.objects.get(id=cart_id)
        # assign cart to customer
        if request.user.is_authenticated and request.user.customer:
            cart.customer = request.user.customer
            cart.save()
        # end
        cart.cartproduct_set.all().delete()
        cart.total = 0
        cart.save()
        messages.success(request, 'All items in cart deleted')        
    return redirect('myCart')

# checkout
def checkout(request):
    form = CheckoutForm
    cart_id = request.session.get('cart_id', None)
    cart_obj = Cart.objects.get(id=cart_id)

    # checkout authentication
    if request.user.is_authenticated and request.user.customer:
        pass
    else:
        return redirect('/loginuser/?next=/checkout/')

    # getting cart
    if cart_id:
        cart_obj = Cart.objects.get(id=cart_id)
        # assign to cart
        if request.user.is_authenticated and request.user.customer:
            cart_obj.customer = request.user.customer
            cart_obj.save()
        # end
    else:
        cart_obj = None

    # form
    if request.method == 'POST':
        form = CheckoutForm(request.POST or None)
        if form.is_valid():
            form = form.save(commit=False)
            form.cart = cart_obj
            form.discount =0
            form.subtotal = cart_obj.total
            form.total = cart_obj.total
            form.order_status = 'Order Received'
            ## new stuff added here
            pay_mth = form.payment_method
            del request.session['cart_id']
            pay_mth = form.payment_method
            form.save()
            order = form.id
            if pay_mth == 'Paystack':
                return redirect('payment', id = order)
            elif pay_mth == 'Payment Transfer':
                return redirect('transfer')

            messages.success(request, 'Order has been placed successfully')
            return redirect('index')
        else:
            messages.success(request, 'No order has been placed')
            return redirect('index')

    context = {
        'cart':cart_obj,
        'form':form,
    }
    return render(request, 'stores/checkout.html', context)

# customer registration

def register(request):
    if request.user.is_authenticated:
        return redirect('index')
    form = CustomerRegister()
    if request.method == 'POST':
        form = CustomerRegister(request.POST or None)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password1')
            password2 = form.cleaned_data.get('password2')            
            if User.objects.filter(username = username).exists():
                messages.warning(request, 'User already exists')
                return redirect('register')
            if User.objects.filter(email = email).exists():
                messages.warning(request, 'Email already exists')
                return redirect('register')
            if password != password2:
                messages.warning(request, 'Passwords do not match')
                return redirect('register')
            user = User.objects.create_user(username,email,password)
            form = form.save(commit=False)
            form.user=user
            form.save()
            messages.success(request, 'Registration successful')
            if "next" in request.GET:
                next_url=request.GET.get("next")
                return redirect(next_url)
            else:
                return redirect('loginuser')
        
    context = {
        'form':form
    }
    return render(request, 'stores/register.html', context)

def loginuser(request):
    if request.user.is_authenticated:
        return redirect('index')    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        users = authenticate(request, username = username, password = password)
        if users is not None:
            login(request, users)
            messages.error(request, 'User login successful')
            if "next" in request.GET:
                next_url=request.GET.get("next")
                return redirect(next_url)
            else:
                return redirect('index')
        else:
            messages.error(request, 'Username / Password not correct')
    return render(request, 'stores/login.html')

def logoutuser(request):
        logout(request)
        messages.success(request, 'Logout Successful')
        return redirect('index')

# profile

def profile(request):
    if request.user.is_authenticated and request.user.customer:
       pass
    else:
        return redirect('loginuser/?next=/profile/')
    customer = request.user.customer
    orders = Order.objects.filter(cart__customer = customer).order_by('-id')
    context = {
        'customer': customer,
        'orders': orders
    }
    return render(request, 'stores/profile.html',context)

# order details of a customer
def orderDetails(request,id):
    if request.user.is_authenticated and request.user.customer:
        order = Order.objects.get(id=id)
        if request.user.customer != order.cart.customer:
            return redirect('profile')
    else:
        return redirect('/loginuser/?next=/profile/')
    orders = Order.objects.get(id=id)
    context = {
        'orders':orders,
    }
    return render(request, 'stores/orderdetail.html', context)

    # search

def search(request):
    thekw = request.GET.get("keyword")
    results = Product.objects.filter(Q(title_icontains=thekw) | Q(description_icontains=thekw))
    context = {
        'results':results,
    }
    return render(request, 'stores/search.html', context)
    
## Payment

def transferPage(request):
    return render(request, 'stores/transfer.html')

def paymentPage(request,id):

    order = Order.objects.get(id=id)

    context = {
        'order': order,
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY
    }
    return render(request, 'stores/payment.html',context)

def verify_payment(request: HttpRequest, ref:str) -> HttpResponse:
    payment = get_object_or_404(Order, ref = ref)
    verified = payment.verify_payment()

    if verified:
        messages.success(request, 'Verification Successful')
    else:
        messages.error(request, 'Verification Failed')
    return redirect('profile')
