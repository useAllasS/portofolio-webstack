from django.shortcuts import render
import random
import json
import torch
from django.views.decorators.csrf import csrf_exempt

from .model import NeuralNet
from .nltk_utils import tokenize, bag_of_words
from django.http import JsonResponse

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
# Load intents data
with open('chatbot/intents.json', 'r') as json_data:
    intents = json.load(json_data)

# Load trained model
FILE = 'chatbot/data.pth'
data = torch.load(FILE)

input_size = data['input_size']
hidden_size = data['hidden_size']
output_size = data['output_size']
all_words = data['all_words']
tags = data['tags']
model_state = data['model_state']

# Initialize model
model = NeuralNet(input_size, hidden_size, output_size).to(device)
model.load_state_dict(model_state)
model.eval()


@csrf_exempt
def chat_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '')  # Retrieve 'message' from the JSON payload

        except json.JSONDecodeError:
            return JsonResponse({'bot_response': 'Invalid JSON payload.'})

        if user_message == 'quit':
            return JsonResponse({'bot_response': 'Chat ended.'})

        sentence = tokenize(user_message)
        X = bag_of_words(sentence, all_words)
        X = X.reshape(1, X.shape[0])
        X = torch.from_numpy(X).to(device)

        output = model(X)
        _, predicted = torch.max(output, dim=1)

        tag = tags[predicted.item()]

        probs = torch.softmax(output, dim=1)
        prob = probs[0][predicted.item()]

        if prob.item() > 0.75:
            for intent in intents['intents']:
                if tag == intent["tag"]:
                    bot_response = random.choice(intent['responses'])
                    return JsonResponse({'bot_response': bot_response})

        bot_response = "I do not understand..."
        return JsonResponse({'bot_response': bot_response})

    return JsonResponse({'bot_response': 'Invalid request method.'})
