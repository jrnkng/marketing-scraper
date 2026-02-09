import os

from google import genai

api_key = os.environ.get("GOOGLE_API_KEY")

# Use AI Studio (API key) if available, otherwise fall back to Vertex AI (ADC)
if api_key:
    client = genai.Client(api_key=api_key)
else: 
    raise ValueError("No API key provided. Please set the GOOGLE_API_KEY environment variable.")

MODEL = "gemini-2.0-flash"


def classify_answer_required_post(title, post_content):
    response = client.models.generate_content(
        model=MODEL,
        contents=f'''
            Does this Reddit post need a response? Reply only YES or NO.
            I have built an interactive planner web app which helps users plan their own hiking itinerary. It features many popular long distance trails, both in Europe, Nepal and the Americas.
            It focuses on allowing users to find and book accommodations. Users can choose their own accommodation and it will calculate route for them.
            Your task is to decide whether the next reddit post is would benefit from me writing a comment to inform them that my tool could help them plan their own trip.
            This could be the case if:
                - The users post is a question related to planning their hike
                - They are seeking advice as to which route to take or where to stay
                - They are asking about general advice for hiking the route
                - They are looking for recommendations on accommodations, huts, or lodging options along popular hiking trails
                - They are expressing uncertainty or confusion about planning aspects of their hike

            Your task is to ONLY reply with YES or NO, nothing else.

            Examples:
            Post: 'I am planning to hike the West Highland Way in September. What kind of weather should I expect and what gear should I bring?' -> NO
            Post: 'Can someone recommend good places to stay along the Tour du Mont Blanc? I'm looking for huts or guesthouses that are conveniently located on the route.' -> YES
            Post: 'What is the best time of year to hike the Annapurna Circuit in Nepal?' -> NO
            Post: 'I'm confused about how to plan my itinerary for the Camino de Santiago. Any tips on how to break up the stages?' -> YES
            Post: 'Worried about how technical the GR20 is. I have some experience but not that confident scrambling' -> NO
            Post: 'I am looking to do a Mediterranean backpacking trip soon for about 15 days. I want to start in Lisbon, Barcelona, Marseille, Cinque Terre. Any tips?' -> NO (this post is about backpacking through cities, not hiking)
            Post: 'What sort of meals do people tend to cook up during a full/multi day hike? An onion, potato, and legumes/beans/meat stews nicely in a mess tin but surely there's some food tips I'm missing from experienced hikers. ' -> NO (about food only)

            Be strict about which posts would benefit from a response. A post should only get a YES if the user would likely benefit from learning about my interactive HIKING planner tool. Topics not related to hiking should be ignored (e.g. roadtrips). 
            Also ignore posts about the US. The planner doesn't feature any US hikes at this time.

            ONLY output YES or NO, nothing else.

            Title: {title}
            Post: {post_content}''',
    )
    return response.text.strip()


def generate_response(post_content):
    response = client.models.generate_content(
        model=MODEL,
        contents=f'''
            You are a helpful Reddit commenter who genuinely wants to assist hikers with their planning questions. A user has posted a question about planning a hike. It can be related to all aspects to planning, finding accommodations, calculating routes or creating an itinerary.
            The webapp is called Traileasy (https://www.traileasy.com).

Your task is to write a helpful, authentic Reddit comment that:
1. Addresses their specific question or concern briefly
2. Naturally mentions that you've built a free interactive planner tool that might help them
3. Includes a brief description of what the tool does (find accommodations, calculate routes, plan itineraries)
4. Does NOT sound like spam or a sales pitch (NO EMOJIS or OVERT MARKETING LANGUAGE)

For example, you might say something like:
"Hi, I think it will be very possible in September. Weather should still be good then! Just bring good rain gear haha but that will be always necessary on the WHW.
For planning your trip and booking accommodations, I've built a free interactive planner webapp that helps you find accommodations and plan your itinerary day by day. It calculates the exact route and distances.
You can check it out at [https://www.traileasy.com](https://www.traileasy.com), you can select the West Highland Way from the homepage and you can choose a standard itinerary (which will pre-load the route). It's completely free. Let me know if it helps :)
"

POST: 'I am thinking about hiking the Dolomites Alta Via 1. Do you have any advice?' Example answer: 'Book accommodations in advance, especially in peak season. I've built a [free interactive planner tool](https://www.traileasy.com) to help find and book huts along the route.'

DONTS:
- Don't speak to broadly about the trip (i.e. don't say 'Since you have a whole month, I think you should also explore the Eastern part of Scotland!')
- Don't include any emojis
- Don't make it sound like a sales pitch (i.e. BAD: By the way, have you looked into any interactive planning tools? I've built a free one that helps with route calculations)

Post: {post_content}

Response:''',
    )
    return response.text
