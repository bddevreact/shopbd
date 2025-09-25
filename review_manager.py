import json
import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from language import t, normalize_lang

class ReviewManager:
    def __init__(self, bot):
        self.bot = bot
        self.reviews = self.load_reviews()
    
    def load_reviews(self):
        """Load reviews from file"""
        try:
            with open('data/reviews.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "reviews": [],
                "statistics": {
                    "total_reviews": 0,
                    "average_rating": 5.0,
                    "rating_distribution": {
                        "5": 0,
                        "4": 0,
                        "3": 0,
                        "2": 0,
                        "1": 0
                    }
                },
                "verified_reviews": 0,
                "featured_reviews": []
            }
    
    def save_reviews(self):
        """Save reviews to file"""
        with open('data/reviews.json', 'w', encoding='utf-8') as f:
            json.dump(self.reviews, f, indent=2, ensure_ascii=False)
    
    def add_review(self, user_id, username, rating, comment, order_id=None):
        """Add a new review"""
        review = {
            "id": len(self.reviews["reviews"]) + 1,
            "user_id": user_id,
            "username": username,
            "rating": rating,
            "comment": comment,
            "order_id": order_id,
            "verified_purchase": order_id is not None,
            "date": datetime.datetime.now().isoformat(),
            "likes": 0,
            "helpful_count": 0
        }
        
        # Add review to list
        self.reviews["reviews"].append(review)
        
        # Update statistics
        self.reviews["statistics"]["total_reviews"] += 1
        self.reviews["statistics"]["rating_distribution"][str(rating)] += 1
        
        # Update average rating
        total_ratings = sum(int(k) * v for k, v in self.reviews["statistics"]["rating_distribution"].items())
        total_reviews = sum(self.reviews["statistics"]["rating_distribution"].values())
        self.reviews["statistics"]["average_rating"] = round(total_ratings / total_reviews, 1) if total_reviews > 0 else 5.0
        
        # Update verified reviews count
        if order_id:
            self.reviews["verified_reviews"] += 1
        
        # Consider adding to featured reviews if rating is high
        if rating >= 4 and len(comment) > 20:
            if len(self.reviews["featured_reviews"]) < 5:
                self.reviews["featured_reviews"].append(review["id"])
        
        self.save_reviews()
        return review["id"]
    
    def get_user_reviews(self, user_id):
        """Get all reviews by a specific user"""
        return [r for r in self.reviews["reviews"] if r["user_id"] == user_id]
    
    def get_review_by_id(self, review_id):
        """Get a specific review by ID"""
        for review in self.reviews["reviews"]:
            if review["id"] == review_id:
                return review
        return None
    
    def delete_review(self, review_id):
        """Delete a review"""
        review = self.get_review_by_id(review_id)
        if review:
            self.reviews["reviews"] = [r for r in self.reviews["reviews"] if r["id"] != review_id]
            self.reviews["statistics"]["total_reviews"] -= 1
            self.reviews["statistics"]["rating_distribution"][str(review["rating"])] -= 1
            
            if review["verified_purchase"]:
                self.reviews["verified_reviews"] -= 1
            
            if review["id"] in self.reviews["featured_reviews"]:
                self.reviews["featured_reviews"].remove(review["id"])
            
            self.save_reviews()
            return True
        return False
    
    def create_review_menu(self, user_id):
        """Create review menu markup"""
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("⭐️ Write a Review", callback_data="write_review"),
            InlineKeyboardButton("📋 My Reviews", callback_data="my_reviews"),
            InlineKeyboardButton("🏆 Top Reviews", callback_data="top_reviews"),
            InlineKeyboardButton("📊 Review Statistics", callback_data="review_stats"),
            InlineKeyboardButton("🔙 Back to Menu", callback_data="back")
        )
        return markup
    
    def format_review_stats(self):
        """Format review statistics for display"""
        stats = self.reviews["statistics"]
        dist = stats["rating_distribution"]
        total = stats["total_reviews"]
        
        stats_text = f"""
⭐️ **Shop Reviews & Ratings**

**Overall Rating:** {stats['average_rating']}/5
**Total Reviews:** {total}
**Verified Reviews:** {self.reviews['verified_reviews']}

**Rating Distribution:**
⭐️⭐️⭐️⭐️⭐️ ({dist['5']} reviews) {'▓' * int(dist['5']*20/total if total else 0)}
⭐️⭐️⭐️⭐️ ({dist['4']} reviews) {'▓' * int(dist['4']*20/total if total else 0)}
⭐️⭐️⭐️ ({dist['3']} reviews) {'▓' * int(dist['3']*20/total if total else 0)}
⭐️⭐️ ({dist['2']} reviews) {'▓' * int(dist['2']*20/total if total else 0)}
⭐️ ({dist['1']} reviews) {'▓' * int(dist['1']*20/total if total else 0)}

**Recent Reviews:**
        """.strip()
        
        return stats_text

def setup_review_handlers(bot, review_manager, user_states):
    """Setup all review-related handlers"""
    
    @bot.callback_query_handler(func=lambda call: call.data in ['write_review', 'my_reviews', 'top_reviews', 'review_stats'])
    def handle_review_callbacks(call):
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        message_id = call.message.message_id
        
        if call.data == 'write_review':
            # Start review process
            user_states[user_id] = {'action': 'writing_review', 'step': 'rating'}
            
            rating_text = """
⭐️ **Write a Review**

How would you rate your experience?
Select your rating (1-5 stars):
            """.strip()
            
            markup = InlineKeyboardMarkup(row_width=5)
            markup.add(
                *[InlineKeyboardButton(f"{'⭐️' * i}", callback_data=f"rate_{i}") for i in range(1, 6)]
            )
            markup.add(InlineKeyboardButton("🔙 Cancel", callback_data="cancel_review"))
            
            bot.edit_message_text(rating_text, chat_id, message_id, reply_markup=markup, parse_mode='Markdown')
        
        elif call.data == 'my_reviews':
            # Show user's reviews
            reviews = review_manager.get_user_reviews(user_id)
            if not reviews:
                text = "You haven't written any reviews yet. Share your experience!"
                markup = InlineKeyboardMarkup()
                markup.add(
                    InlineKeyboardButton("✍️ Write a Review", callback_data="write_review"),
                    InlineKeyboardButton("🔙 Back", callback_data="back")
                )
            else:
                text = "**Your Reviews:**\n\n"
                for review in reviews[-5:]:  # Show last 5 reviews
                    text += f"{'⭐️' * review['rating']} - {review['date'][:10]}\n{review['comment'][:100]}...\n\n"
                markup = InlineKeyboardMarkup()
                markup.add(
                    InlineKeyboardButton("✍️ Write Another Review", callback_data="write_review"),
                    InlineKeyboardButton("🔙 Back", callback_data="back")
                )
            
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode='Markdown')
        
        elif call.data == 'top_reviews':
            # Show featured/top reviews
            featured = []
            for review_id in review_manager.reviews["featured_reviews"]:
                review = review_manager.get_review_by_id(review_id)
                if review:
                    featured.append(review)
            
            if not featured:
                text = "No featured reviews yet. Be the first to share your experience!"
                markup = InlineKeyboardMarkup()
                markup.add(
                    InlineKeyboardButton("✍️ Write a Review", callback_data="write_review"),
                    InlineKeyboardButton("🔙 Back", callback_data="back")
                )
            else:
                text = "🏆 **Featured Reviews**\n\n"
                for review in featured:
                    text += f"""
{'⭐️' * review['rating']} by @{review['username']}
"{review['comment'][:100]}..."
{'✅ Verified Purchase' if review['verified_purchase'] else ''}
                    """.strip() + "\n\n"
                markup = InlineKeyboardMarkup()
                markup.add(
                    InlineKeyboardButton("✍️ Write a Review", callback_data="write_review"),
                    InlineKeyboardButton("🔙 Back", callback_data="back")
                )
            
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode='Markdown')
        
        elif call.data == 'review_stats':
            # Show review statistics
            stats_text = review_manager.format_review_stats()
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("✍️ Write a Review", callback_data="write_review"),
                InlineKeyboardButton("🔙 Back", callback_data="back")
            )
            
            bot.edit_message_text(stats_text, chat_id, message_id, reply_markup=markup, parse_mode='Markdown')
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('rate_'))
    def handle_rating_selection(call):
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        message_id = call.message.message_id
        
        if user_id in user_states and user_states[user_id].get('action') == 'writing_review':
            rating = int(call.data.split('_')[1])
            user_states[user_id]['rating'] = rating
            user_states[user_id]['step'] = 'comment'
            
            comment_text = f"""
⭐️ **Write a Review**

Selected Rating: {'⭐️' * rating}

Please write your review comment below. Share your experience in detail!

**Tips for a great review:**
• What did you like most?
• How was the service?
• Would you recommend it?
• Any suggestions for improvement?

Type your review comment or click Cancel.
            """.strip()
            
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔙 Cancel", callback_data="cancel_review"))
            
            bot.edit_message_text(comment_text, chat_id, message_id, reply_markup=markup, parse_mode='Markdown')
    
    @bot.callback_query_handler(func=lambda call: call.data == 'cancel_review')
    def handle_review_cancel(call):
        user_id = call.from_user.id
        if user_id in user_states:
            user_states.pop(user_id)
        
        bot.answer_callback_query(call.id, "Review cancelled")
        bot.edit_message_text(
            "Review cancelled. Return to menu?",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=review_manager.create_review_menu(user_id)
        )
    
    @bot.message_handler(func=lambda message: message.from_user.id in user_states and user_states[message.from_user.id].get('action') == 'writing_review' and user_states[message.from_user.id].get('step') == 'comment')
    def handle_review_comment(message):
        user_id = message.from_user.id
        state = user_states[user_id]
        
        if len(message.text) < 10:
            bot.reply_to(message, "Please write a more detailed review (at least 10 characters).")
            return
        
        # Add the review
        review_id = review_manager.add_review(
            user_id=user_id,
            username=message.from_user.username or "Anonymous",
            rating=state['rating'],
            comment=message.text
        )
        
        # Clear the state
        user_states.pop(user_id)
        
        # Send confirmation
        confirmation_text = f"""
✅ **Thank you for your review!**

Rating: {'⭐️' * state['rating']}
Review ID: #{review_id}

Your review has been published and will help other users make informed decisions.
        """.strip()
        
        bot.reply_to(message, confirmation_text, reply_markup=review_manager.create_review_menu(user_id), parse_mode='Markdown')