import tensorflow as tf
import numpy as np
from tensorflow.keras.preprocessing import image
import matplotlib.pyplot as plt
from tensorflow.keras.applications import imagenet_utils
from IPython.display import Image
from .forms import ImageUploadForm
from django.shortcuts import render
from .models import Product

import tensorflow as tf
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.mobilenet_v2 import MobileNetV2, preprocess_input
from PIL import Image

import os

from django.shortcuts import render, redirect, reverse
from . import forms, models
from django.http import HttpResponseRedirect, HttpResponse
from django.core.mail import send_mail
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomerForm, CustomerUserForm
from django.shortcuts import render, get_object_or_404
from .models import Category, Product
from .forms import ProductForm
import paypalrestsdk
from django.conf import settings
from ecom.utils import classifierMobileNet

from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import redirect
from django.views.generic import View

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from ecommerce.settings import GOOGLE_OAUTH2_CLIENT_ID, GOOGLE_OAUTH2_CLIENT_SECRET, GOOGLE_OAUTH2_REDIRECT_URI

from .models import Product
from PIL import Image
from tensorflow.keras.applications.mobilenet import MobileNet
from tensorflow.keras.applications.mobilenet import preprocess_input, decode_predictions
import numpy as np
from skimage.transform import resize
from django.shortcuts import render
from .models import Product
from django.shortcuts import render
from .models import Product, Category
###################################################
from .models import Orders
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity


def recommendation_view(request):
    # products = Product.objects.all()
    # Retrieve the necessary data from the database
    orders = Orders.objects.filter(quantity__gt=0).exclude(customer=None).values()
    orders_df = pd.DataFrame.from_records(orders)

    # Perform the recommendation logic
    customer_item_matrix = orders_df.pivot_table(
        index='customer_id',
        columns='product_id',
        values='quantity',
        aggfunc='sum'
    )

    customer_item_matrix = customer_item_matrix.fillna(0)
    customer_item_matrix = customer_item_matrix.applymap(lambda x: 1 if x > 0 else 0)
    user_user_sim_matrix = pd.DataFrame(cosine_similarity(customer_item_matrix))
    user_user_sim_matrix.columns = customer_item_matrix.index
    user_user_sim_matrix.index = customer_item_matrix.index

    customer_id_A = 12347.0
    customer_id_B = 14696.0

    items_bought_by_A = customer_item_matrix.loc[customer_id_A][customer_item_matrix.loc[customer_id_A] > 0]
    items_bought_by_B = customer_item_matrix.loc[customer_id_B][customer_item_matrix.loc[customer_id_B] > 0]
    items_to_recommend_to_B = set(items_bought_by_A.index) - set(items_bought_by_B.index)

    # Retrieve the recommended items based on the item IDs
    recommended_items = Orders.objects.filter(product_id__in=items_to_recommend_to_B).distinct()

    # Pass the necessary data to the template
    context = {
        'recommended_items': recommended_items,
        # 'products': products,
    }

    return render(request, 'ecom/recommended_products.html', context)


def home_view(request):
    products = models.Product.objects.all()
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter = product_ids.split('|')
        product_count_in_cart = len(set(counter))
    else:
        product_count_in_cart = 0
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')
    return render(request, 'ecom/index.html', {'products': products, 'product_count_in_cart': product_count_in_cart})


# for showing login button for admin(SMI S6 TRIO)
def adminclick_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')
    return HttpResponseRedirect('adminlogin')


def customer_signup_view(request):
    if request.method == 'POST':
        userForm = CustomerUserForm(request.POST)
        customerForm = CustomerForm(request.POST, request.FILES)
        if userForm.is_valid() and customerForm.is_valid():
            user = userForm.save()
            user.set_password(user.password)
            user.save()
            customer = customerForm.save(commit=False)
            customer.user = user
            customer.save()
            group = Group.objects.get(name='CUSTOMER')
            group.user_set.add(user)  # add user to the CUSTOMER group
            messages.success(request, 'Account created successfully!')
            return HttpResponseRedirect('customerlogin')
        else:
            print("Forms are invalid")
            print(userForm.errors)
            print(customerForm.errors)
    else:
        userForm = CustomerUserForm()
        customerForm = CustomerForm()
    return render(request, 'ecom/customersignup.html', {'userForm': userForm, 'customerForm': customerForm})


# -----------for checking user iscustomer
def is_customer(user):
    return user.groups.filter(name='CUSTOMER').exists()


# ---------AFTER ENTERING CREDENTIALS WE CHECK WHETHER USERNAME AND PASSWORD IS OF ADMIN,CUSTOMER
def afterlogin_view(request):
    if is_customer(request.user):
        return redirect('customer-home')
    else:
        return redirect('admin-dashboard')


# ---------------------------------------------------------------------------------
# ------------------------ ADMIN RELATED VIEWS START ------------------------------
# ---------------------------------------------------------------------------------
@login_required(login_url='adminlogin')
def admin_dashboard_view(request):
    # for cards on dashboard
    customercount = models.Customer.objects.all().count()
    productcount = models.Product.objects.all().count()
    ordercount = models.Orders.objects.all().count()

    # for recent order tables
    orders = models.Orders.objects.all()
    ordered_products = []
    ordered_bys = []
    for order in orders:
        ordered_product = models.Product.objects.all().filter(id=order.product.id)
        ordered_by = models.Customer.objects.all().filter(id=order.customer.id)
        ordered_products.append(ordered_product)
        ordered_bys.append(ordered_by)

    mydict = {
        'customercount': customercount,
        'productcount': productcount,
        'ordercount': ordercount,
        'data': zip(ordered_products, ordered_bys, orders),
    }
    return render(request, 'ecom/admin_dashboard.html', context=mydict)


# admin view customer table
@login_required(login_url='adminlogin')
def view_customer_view(request):
    customers = models.Customer.objects.all()
    return render(request, 'ecom/view_customer.html', {'customers': customers})


# admin delete customer
@login_required(login_url='adminlogin')
def delete_customer_view(request, pk):
    customer = models.Customer.objects.get(id=pk)
    user = models.User.objects.get(id=customer.user_id)
    user.delete()
    customer.delete()
    return redirect('view-customer')


@login_required(login_url='adminlogin')
def update_customer_view(request, pk):
    customer = models.Customer.objects.get(id=pk)
    user = models.User.objects.get(id=customer.user_id)
    userForm = forms.CustomerUserForm(instance=user)
    customerForm = forms.CustomerForm(request.FILES, instance=customer)
    mydict = {'userForm': userForm, 'customerForm': customerForm}
    if request.method == 'POST':
        userForm = forms.CustomerUserForm(request.POST, instance=user)
        customerForm = forms.CustomerForm(request.POST, instance=customer)
        if userForm.is_valid() and customerForm.is_valid():
            user = userForm.save()
            user.set_password(user.password)
            user.save()
            customerForm.save()
            return redirect('view-customer')
    return render(request, 'ecom/admin_update_customer.html', context=mydict)


# admin view the product
@login_required(login_url='adminlogin')
def admin_products_view(request):
    products = models.Product.objects.all()
    return render(request, 'ecom/admin_products.html', {'products': products})


# admin add product by clicking on floating button
@login_required(login_url='adminlogin')
def admin_add_product_view(request):
    categories = ['pc', 'camera', 'moto', 'voiture', 'velo', 'phone', 'ordinateur', 'tv']
    for category in categories:
        Category.objects.get_or_create(name=category)

    if request.method == 'POST':
        productForm = ProductForm(request.POST, request.FILES)
        if productForm.is_valid():
            product = productForm.save(commit=False)
            product.save()

            selected_categories = request.POST.getlist('categories')
            categories = Category.objects.filter(id__in=selected_categories)
            product.categories.set(categories)

            return HttpResponseRedirect('admin-products')
    else:
        productForm = ProductForm()

    return render(request, 'ecom/admin_add_products.html', {'productForm': productForm})


@login_required(login_url='adminlogin')
def delete_product_view(request, pk):
    product = models.Product.objects.get(id=pk)
    product.delete()
    return redirect('admin-products')


@login_required(login_url='adminlogin')
def update_product_view(request, pk):
    product = models.Product.objects.get(id=pk)
    if request.method == 'POST':
        productForm = forms.ProductForm(request.POST, request.FILES, instance=product)
        if productForm.is_valid():
            productForm.save()
            return redirect('admin-products')
    else:
        productForm = forms.ProductForm(instance=product)

    return render(request, 'ecom/admin_update_product.html', {'productForm': productForm})


@login_required(login_url='adminlogin')
def admin_view_booking_view(request):
    orders = models.Orders.objects.all()
    ordered_products = []
    ordered_bys = []
    for order in orders:
        ordered_product = models.Product.objects.all().filter(id=order.product.id)
        ordered_by = models.Customer.objects.all().filter(id=order.customer.id)
        ordered_products.append(ordered_product)
        ordered_bys.append(ordered_by)
    return render(request, 'ecom/admin_view_booking.html', {'data': zip(ordered_products, ordered_bys, orders)})


@login_required(login_url='adminlogin')
def delete_order_view(request, pk):
    order = models.Orders.objects.get(id=pk)
    order.delete()
    return redirect('admin-view-booking')


# for changing status of order (pending,delivered...)
@login_required(login_url='adminlogin')
def update_order_view(request, pk):
    order = models.Orders.objects.get(id=pk)
    orderForm = forms.OrderForm(instance=order)
    if request.method == 'POST':
        orderForm = forms.OrderForm(request.POST, instance=order)
        if orderForm.is_valid():
            orderForm.save()
            return redirect('admin-view-booking')
    return render(request, 'ecom/update_order.html', {'orderForm': orderForm})


# admin view the feedback
@login_required(login_url='adminlogin')
def view_feedback_view(request):
    feedbacks = models.Feedback.objects.all().order_by('-id')
    return render(request, 'ecom/view_feedback.html', {'feedbacks': feedbacks})


# ---------------------------------------------------------------------------------
# ------------------------ PUBLIC CUSTOMER RELATED VIEWS START ---------------------
# ---------------------------------------------------------------------------------
def search_view(request):
    # whatever user write in search box we get in query
    query = request.GET['query']
    products = models.Product.objects.all().filter(name__icontains=query)
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter = product_ids.split('|')
        product_count_in_cart = len(set(counter))
    else:
        product_count_in_cart = 0

    # word variable will be shown in html when user click on search button
    word = "Searched Result :"

    if request.user.is_authenticated:
        return render(request, 'ecom/customer_home.html',
                      {'products': products, 'word': word, 'product_count_in_cart': product_count_in_cart})
    return render(request, 'ecom/index.html',
                  {'products': products, 'word': word, 'product_count_in_cart': product_count_in_cart})


# any one can add product to cart, no need of signin
def add_to_cart_view(request, pk):
    products = models.Product.objects.all()

    # for cart counter, fetching products ids added by customer from cookies
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter = product_ids.split('|')
        product_count_in_cart = len(set(counter))
    else:
        product_count_in_cart = 1

    response = render(request, 'ecom/index.html',
                      {'products': products, 'product_count_in_cart': product_count_in_cart})

    # adding product id to cookies
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        if product_ids == "":
            product_ids = str(pk)
        else:
            product_ids = product_ids + "|" + str(pk)
        response.set_cookie('product_ids', product_ids)
    else:
        response.set_cookie('product_ids', pk)

    product = models.Product.objects.get(id=pk)
    messages.info(request, product.name + ' added to cart successfully!')

    return response


# for checkout of cart
def cart_view(request):
    # for cart counter
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter = product_ids.split('|')
        product_count_in_cart = len(set(counter))
    else:
        product_count_in_cart = 0

    # fetching product details from db whose id is present in cookie
    products = None
    total = 0.0
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        if product_ids != "":
            product_id_in_cart = product_ids.split('|')
            products = models.Product.objects.all().filter(id__in=product_id_in_cart)

            # for total price shown in cart
            for p in products:
                total = total + float(p.price)
    return render(request, 'ecom/cart.html',
                  {'products': products, 'total': total, 'product_count_in_cart': product_count_in_cart})


def remove_from_cart_view(request, pk):
    # for counter in cart
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter = product_ids.split('|')
        product_count_in_cart = len(set(counter))
    else:
        product_count_in_cart = 0

    # removing product id from cookie
    total = 0
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        product_id_in_cart = product_ids.split('|')
        product_id_in_cart = list(set(product_id_in_cart))
        product_id_in_cart.remove(str(pk))
        products = models.Product.objects.all().filter(id__in=product_id_in_cart)
        # for total price shown in cart after removing product
        for p in products:
            total = total + p.price

        #  for update coookie value after removing product id in cart
        value = ""
        for i in range(len(product_id_in_cart)):
            if i == 0:
                value = value + product_id_in_cart[0]
            else:
                value = value + "|" + product_id_in_cart[i]
        response = render(request, 'ecom/cart.html',
                          {'products': products, 'total': total, 'product_count_in_cart': product_count_in_cart})
        if value == "":
            response.delete_cookie('product_ids')
        response.set_cookie('product_ids', value)
        return response


def send_feedback_view(request):
    feedbackForm = forms.FeedbackForm()
    if request.method == 'POST':
        feedbackForm = forms.FeedbackForm(request.POST)
        if feedbackForm.is_valid():
            feedbackForm.save()
            return render(request, 'ecom/feedback_sent.html')
    return render(request, 'ecom/send_feedback.html', {'feedbackForm': feedbackForm})


def category_view(request, category):
    category = Category.objects.get(name=category)
    products = Product.objects.filter(categories=category)
    context = {'products': products, 'category': category}
    return render(request, 'ecom/category.html', context)


# ---------------------------------------------------------------------------------
# ------------------------ CUSTOMER RELATED VIEWS START ------------------------------
# ---------------------------------------------------------------------------------
@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def customer_home_view(request):
    products = Product.objects.all()

    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter = product_ids.split('|')
        product_count_in_cart = len(set(counter))
    else:
        product_count_in_cart = 0

    recommended_items = []  # Placeholder for recommended items

    # Add logic to retrieve the recommended items
    # products = Product.objects.all()
    # Retrieve the necessary data from the database
    orders = Orders.objects.filter(quantity__gt=0).exclude(customer=None).values()
    orders_df = pd.DataFrame.from_records(orders)

    # Perform the recommendation logic
    customer_item_matrix = orders_df.pivot_table(
        index='customer_id',
        columns='product_id',
        values='quantity',
        aggfunc='sum'
    )

    customer_item_matrix = customer_item_matrix.fillna(0)
    customer_item_matrix = customer_item_matrix.applymap(lambda x: 1 if x > 0 else 0)
    user_user_sim_matrix = pd.DataFrame(cosine_similarity(customer_item_matrix))
    user_user_sim_matrix.columns = customer_item_matrix.index
    user_user_sim_matrix.index = customer_item_matrix.index

    customer_id_A = 12347.0
    customer_id_B = 14696.0

    items_bought_by_A = customer_item_matrix.loc[customer_id_A][customer_item_matrix.loc[customer_id_A] > 0]
    items_bought_by_B = customer_item_matrix.loc[customer_id_B][customer_item_matrix.loc[customer_id_B] > 0]
    items_to_recommend_to_B = set(items_bought_by_A.index) - set(items_bought_by_B.index)

    # Retrieve the recommended items based on the item IDs
    recommended_items = Orders.objects.filter(product_id__in=items_to_recommend_to_B).distinct()

    # Populate the recommended_items list with the recommended products

    context = {
        'products': products,
        'product_count_in_cart': product_count_in_cart,
        'recommended_items': recommended_items,  # Pass the recommended_items list to the template
    }

    return render(request, 'ecom/customer_home.html', context)


# shipment address before placing order
@login_required(login_url='customerlogin')
def customer_address_view(request):
    # this is for checking whether product is present in cart or not
    # if there is no product in cart we will not show address form
    product_in_cart = False
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        if product_ids != "":
            product_in_cart = True
    # for counter in cart
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter = product_ids.split('|')
        product_count_in_cart = len(set(counter))
    else:
        product_count_in_cart = 0

    addressForm = forms.AddressForm()
    if request.method == 'POST':
        addressForm = forms.AddressForm(request.POST)
        if addressForm.is_valid():
            # here we are taking address, email, mobile at time of order placement
            # we are not taking it from customer account table because
            # these thing can be changes
            email = addressForm.cleaned_data['Email']
            mobile = addressForm.cleaned_data['Mobile']
            address = addressForm.cleaned_data['Address']
            # for showing total price on payment page.....accessing id from cookies then fetching  price of product
            # from db
            total = 0
            if 'product_ids' in request.COOKIES:
                product_ids = request.COOKIES['product_ids']
            if product_ids != "":
                product_id_in_cart = product_ids.split('|')
                products = models.Product.objects.all().filter(id__in=product_id_in_cart)
                for p in products:
                    total = total + p.price

            # Create a PayPal payment
            paypalrestsdk.configure({
                'mode': 'sandbox',  # Use 'live' for production
                'client_id': settings.PAYPAL_CLIENT_ID,
                'client_secret': settings.PAYPAL_CLIENT_SECRET
            })

            payment = paypalrestsdk.Payment({
                'intent': 'sale',
                'payer': {
                    'payment_method': 'paypal'
                },
                'redirect_urls': {
                    'return_url': request.build_absolute_uri('/payment-success'),
                    'cancel_url': request.build_absolute_uri('/')
                },
                'transactions': [{
                    'amount': {
                        'total': str(total),
                        'currency': 'USD'
                    }
                }]
            })

            if payment.create():
                # Save the payment ID in the session
                request.session['payment_id'] = payment.id

                # Redirect to PayPal for user authorization
                for link in payment.links:
                    if link.method == 'REDIRECT':
                        return redirect(link.href)
                else:
                    return redirect('/')
            else:
                # Payment creation failed, handle the error
                return render(request, 'ecom/payment.html', {'total': total, 'error': payment.error})

    return render(request, 'ecom/customer_address.html',
                  {'addressForm': addressForm, 'product_in_cart': product_in_cart,
                   'product_count_in_cart': product_count_in_cart})


# here we are just directing to this view...actually we have to check whther payment is successful or not
# then only this view should be accessed

@login_required(login_url='customerlogin')
@csrf_exempt
def payment_success_view(request):
    payment_id = request.GET.get('paymentId')
    payer_id = request.GET.get('PayerID')

    if payment_id and payer_id:
        # Retrieve the payment details from PayPal
        paypalrestsdk.configure({
            'mode': 'sandbox',  # Use 'live' for production
            'client_id': settings.PAYPAL_CLIENT_ID,
            'client_secret': settings.PAYPAL_CLIENT_SECRET
        })

        payment = paypalrestsdk.Payment.find(payment_id)
        if payment.execute({'payer_id': payer_id}):
            # Payment successful, show the payment success page
            # Here you can add the logic to create orders and update the database accordingly

            # Delete cookies after order placement
            response = render(request, 'ecom/payment_success.html')
            response.delete_cookie('product_ids')
            response.delete_cookie('email')
            response.delete_cookie('mobile')
            response.delete_cookie('address')
            return response
        else:
            # Payment execution failed, handle the error
            return render(request, 'ecom/payment.html', {'error': payment.error})

    return redirect('/')

    # after order placed cookies should be deleted
    response = render(request, 'ecom/payment_success.html')
    response.delete_cookie('product_ids')
    response.delete_cookie('email')
    response.delete_cookie('mobile')
    response.delete_cookie('address')
    return response


@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def my_order_view(request):
    customer = models.Customer.objects.get(user_id=request.user.id)
    orders = models.Orders.objects.all().filter(customer_id=customer)
    ordered_products = []
    for order in orders:
        ordered_product = models.Product.objects.all().filter(id=order.product.id)
        ordered_products.append(ordered_product)

    return render(request, 'ecom/my_order.html', {'data': zip(ordered_products, orders)})


# @login_required(login_url='customerlogin')
# @user_passes_test(is_customer)
# def my_order_view2(request):

#     products=models.Product.objects.all()
#     if 'product_ids' in request.COOKIES:
#         product_ids = request.COOKIES['product_ids']
#         counter=product_ids.split('|')
#         product_count_in_cart=len(set(counter))
#     else:
#         product_count_in_cart=0
#     return render(request,'ecom/my_order.html',{'products':products,'product_count_in_cart':product_count_in_cart})    


# --------------for discharge patient bill (pdf) download and printing
import io
from xhtml2pdf import pisa
from django.template.loader import get_template
from django.template import Context
from django.http import HttpResponse


def render_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    html = template.render(context_dict)
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("ISO-8859-1")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return


@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def download_invoice_view(request, orderID, productID):
    order = models.Orders.objects.get(id=orderID)
    product = models.Product.objects.get(id=productID)
    mydict = {
        'orderDate': order.order_date,
        'customerName': request.user,
        'customerEmail': order.email,
        'customerMobile': order.mobile,
        'shipmentAddress': order.address,
        'orderStatus': order.status,

        'productName': product.name,
        'productImage': product.product_image,
        'productPrice': product.price,
        'productDescription': product.description,

    }
    return render_to_pdf('ecom/download_invoice.html', mydict)


@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def my_profile_view(request):
    customer = models.Customer.objects.get(user_id=request.user.id)
    return render(request, 'ecom/my_profile.html', {'customer': customer})


@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def edit_profile_view(request):
    customer = models.Customer.objects.get(user_id=request.user.id)
    user = models.User.objects.get(id=customer.user_id)
    if request.method == 'POST':
        userForm = forms.CustomerUserForm(request.POST, instance=user)
        customerForm = forms.CustomerForm(request.POST, request.FILES, instance=customer)
        if userForm.is_valid() and customerForm.is_valid():
            user = userForm.save()
            user.set_password(user.password)
            user.save()
            customerForm.save()
            return HttpResponseRedirect('my-profile')
    else:
        userForm = forms.CustomerUserForm(instance=user)
        customerForm = forms.CustomerForm(instance=customer)
    mydict = {'userForm': userForm, 'customerForm': customerForm}
    return render(request, 'ecom/edit_profile.html', context=mydict)


# ---------------------------------------------------------------------------------
# ------------------------ ABOUT US AND CONTACT US VIEWS START --------------------
# ---------------------------------------------------------------------------------
def aboutus_view(request):
    return render(request, 'ecom/aboutus.html')


def contactus_view(request):
    sub = forms.ContactusForm()
    if request.method == 'POST':
        sub = forms.ContactusForm(request.POST)
        if sub.is_valid():
            email = sub.cleaned_data['Email']
            name = sub.cleaned_data['Name']
            message = sub.cleaned_data['Message']
            send_mail(str(name) + ' || ' + str(email), message, settings.EMAIL_HOST_USER, settings.EMAIL_RECEIVING_USER,
                      fail_silently=False)
            return render(request, 'ecom/contactussuccess.html')
    return render(request, 'ecom/contactus.html', {'form': sub})


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'ecom/product_detail.html', {'product': product})


class GoogleLoginView(View):
    def get(self, request):
        flow = Flow.from_client_config(
            client_config={
                'client_id': GOOGLE_OAUTH2_CLIENT_ID,
                'client_secret': GOOGLE_OAUTH2_CLIENT_SECRET,
                'redirect_uris': [GOOGLE_OAUTH2_REDIRECT_URI],
                'scope': ['openid', 'profile', 'email'],
            },
            scopes=['openid', 'profile', 'email'],
            state=request.GET.get('state', ''),
        )
        auth_url, _ = flow.authorization_url(prompt='consent')
        return redirect(auth_url)


class GoogleLoginCallbackView(View):
    def get(self, request):
        flow = Flow.from_client_config(
            client_config={
                'client_id': settings.GOOGLE_OAUTH2_CLIENT_ID,
                'client_secret': settings.GOOGLE_OAUTH2_CLIENT_SECRET,
                'redirect_uris': [settings.GOOGLE_OAUTH2_REDIRECT_URI],
                'scope': ['openid', 'profile', 'email'],
            },
            scopes=['openid', 'profile', 'email'],
            state=request.GET.get('state', ''),
        )
        flow.fetch_token(authorization_response=request.build_absolute_uri())
        credentials = flow.credentials

        # Create or update the user as needed
        # For example:
        # user = User.objects.filter(email=credentials.id_token['email']).first()
        # if user is None:
        #     user = User.objects.create_user(username=credentials.id_token['email'], email=credentials.id_token['email'])
        # user.first_name = credentials.id_token.get('given_name', '')
        # user.last_name = credentials.id_token.get('family_name', '')
        # user.save()

        # Log in the user
        # For example:
        # login(request, user)

        # Redirect to the customer home view
        return redirect('customer-home')


PAYPAL_CLIENT_ID = 'AX99_izPx3B72EhWKqFA6HHi9oqP97jzwq8DkaZNml1Y9vX60RFljWUHxoRA7THWp1aDjrgIYbiOwhkg'
PAYPAL_CLIENT_SECRET = 'EAIGwkbFkOiv8AeP10yMTxGqGv-t4frnStc4wJ0hqydYkBTw4s6aEZ8rQOU1P0B8yXkydgfDP-raK_Pf'


# ---------------------------------------------------------------------------------
# ------------------------ Image Recognition Views --------------------
# ---------------------------------------------------------------------------------


########################### fonction de classification ###########################
####################################################


def classifierMobileNet(img_path):
    # Load the MobileNetV2 model
    model = MobileNetV2(weights='imagenet')

    # Load and preprocess the image
    img = image.load_img(img_path, target_size=(224, 224))
    img = image.img_to_array(img)
    img = preprocess_input(img)
    img = tf.expand_dims(img, axis=0)

    # Make predictions
    predictions = model.predict(img)
    predicted_labels = tf.keras.applications.imagenet_utils.decode_predictions(predictions, top=1)

    # Get the predicted category
    predicted_category = predicted_labels[0][0][1]

    return predicted_category


def homebase(request):
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():

            # Save the uploaded image temporarily
            image = form.cleaned_data['image']
            with open('temp_image.jpg', 'wb') as f:
                f.write(image.read())

            # Classify the image using the classifier function
            predicted_category = classifierMobileNet('temp_image.jpg')

            predicted_category = get_categorie(predicted_category)
            print("-----------------------------------------------------")
            print(predicted_category)
            print("-----------------------------------------------------")
            # Get the category object from the predicted category name
            try:
                category = Category.objects.get(name=predicted_category)
                products = Product.objects.filter(categories=category)
                context = {'products': products, 'category': category}
                print("-----------------------------------------------------")
                print(products)
                print("-----------------------------------------------------")

                return render(request, 'ecom/category.html', context)
            except Category.DoesNotExist:
                print("-------------- not found -------------")
                # Handle the case when the category is not found
                return render(request, 'ecom/category.html')
    else:
        form = ImageUploadForm()

    context = {'form': form}
    return render(request, 'ecom/homebase.html', context)


def homebase2(request):
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Save the uploaded image temporarily
            image = form.cleaned_data['image']
            with open('temp_image.jpg', 'wb') as f:
                f.write(image.read())

            # Classify the image using the classifier function
            predicted_category = classifierMobileNet('temp_image.jpg')

            # Get the category object from the predicted category name
            try:
                category = Category.objects.get(name=predicted_category)
                products = Product.objects.filter(categories=category)
                context = {'products': products, 'category': category}
                return render(request, 'ecom/category.html', context)
            except Category.DoesNotExist:
                # Handle the case when the category is not found
                return redirect('homebase')
    else:
        form = ImageUploadForm()

    context = {'form': form}
    return render(request, 'homebase.html', context)


########################################### fonction Get Categorie ######################################
def get_categorie(nom):
    nom = nom.lower()
    pc = ["laptop", "notebook", 'Portable']
    accessoire_info = ["mouse", 'modem', 'hard_disc', "keyboard", "device", 'disk drive', 'disc drive', 'hard drive',
                       'winchester drive', 'drive', 'external drive', 'ram', 'ipod', 'cd', 'disk', 'dur']
    camera = ["camera", "kodak", 'Flash', 'photoflash', 'flash lamp', 'flashgun', 'flashbulb', 'flash bulb',
              'spotlight']
    moto = ['motor scooter', 'scouter', 'motor']
    voiture = ['car', 'railcar', 'railway', 'railroad', 'wagon']
    velo = ['bicycle', 'bike', 'wheel', 'cycle']
    phone = ['telephone', 'phone', 'cellphone', 'cell', 'mobile phone', 'mobile']
    tv = ['television', 'television system', 'tv', 'monitor']
    ordinateur = ['desktop', 'Computer', 'computing machine', 'computing device', 'data processor',
                  'electronic computer', 'information processing system']
    for p in pc:
        if p in nom:
            return "pc"
    for p in accessoire_info:
        if p in nom:
            return "accessoire_info"
    for p in camera:
        if p in nom:
            return "camera"
    for p in moto:
        if p in nom:
            return "moto"
    for p in voiture:
        if p in nom:
            return "voiture"
    for p in velo:
        if p in nom:
            return "velo"
    for p in phone:
        if p in nom:
            return "phone"
    for p in tv:
        if p in nom:
            return "tv"
    for p in ordinateur:
        if p in nom:
            return "ordinateur"

    return "rien"
