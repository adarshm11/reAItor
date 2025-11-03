"""
Recommendation Service
Learns from user feedback (swipes) and provides personalized listing rankings
"""

import chromadb
from typing import List, Dict, Optional, Tuple
from models.schemas import FinalReport, FeedbackRequest, Listing
from collections import defaultdict
import json
import numpy as np


class RecommendationService:
    """Service for learning user preferences and ranking listings"""

    def __init__(self):
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path="./chroma_data")

        # Create or get collections
        self.feedback_collection = self.client.get_or_create_collection(
            name="user_feedback",
            metadata={"description": "User swipe feedback for preference learning"}
        )

        self.preference_weights_collection = self.client.get_or_create_collection(
            name="preference_weights",
            metadata={"description": "Learned feature weights per user session"}
        )

    def record_feedback(
        self,
        feedback: FeedbackRequest,
        listing: Listing,
        final_report: FinalReport
    ):
        """
        Record user feedback (swipe) for a listing

        Args:
            feedback: User's swipe action (like/dislike)
            listing: The property listing
            final_report: The full report including scores
        """
        # Extract features from the listing and report
        features = self._extract_features(listing, final_report)

        # Create document for storage
        document = json.dumps({
            "session_id": feedback.session_id,
            "listing_id": feedback.listing_id,
            "action": feedback.action,
            "features": features,
            "timestamp": str(chromadb.utils.embedding_functions.DefaultEmbeddingFunction)
        })

        # Metadata for filtering and analysis
        metadata = {
            "session_id": feedback.session_id,
            "listing_id": feedback.listing_id,
            "action": feedback.action,
            "price": listing.price,
            "bedrooms": listing.bedrooms,
            "bathrooms": listing.bathrooms,
            "sqft": listing.sqft,
            "final_score": final_report.final_score,
        }

        # Store in ChromaDB
        feedback_id = f"{feedback.session_id}_{feedback.listing_id}"
        self.feedback_collection.upsert(
            documents=[document],
            metadatas=[metadata],
            ids=[feedback_id]
        )

        # Update learned weights for this session
        self._update_preference_weights(feedback.session_id)

    def get_ranked_listings(
        self,
        session_id: str,
        listings: List[FinalReport]
    ) -> List[FinalReport]:
        """
        Rank listings based on learned user preferences

        Args:
            session_id: User's session ID
            listings: List of final reports to rank

        Returns:
            Ranked list of final reports (best first)
        """
        # Get learned weights for this session
        weights = self._get_preference_weights(session_id)

        if not weights:
            # No learning data yet, return sorted by original final_score
            return sorted(listings, key=lambda x: x.final_score, reverse=True)

        # Calculate personalized scores
        scored_listings = []
        for report in listings:
            features = self._extract_features(report.listing, report)
            personalized_score = self._calculate_personalized_score(features, weights)
            scored_listings.append((personalized_score, report))

        # Sort by personalized score (highest first)
        scored_listings.sort(key=lambda x: x[0], reverse=True)

        return [report for _, report in scored_listings]

    def get_next_listing(
        self,
        session_id: str,
        available_listings: List[FinalReport],
        seen_listing_ids: List[str]
    ) -> Optional[FinalReport]:
        """
        Get the next best listing for the user to review

        Args:
            session_id: User's session ID
            available_listings: All available listings
            seen_listing_ids: IDs of listings already shown

        Returns:
            Next best listing or None if no unseen listings
        """
        # Filter out already seen listings
        unseen_listings = [
            listing for listing in available_listings
            if listing.listing.id not in seen_listing_ids
        ]

        if not unseen_listings:
            return None

        # Rank unseen listings
        ranked = self.get_ranked_listings(session_id, unseen_listings)

        # Return top listing
        return ranked[0] if ranked else None

    def get_learning_insights(self, session_id: str) -> Dict:
        """
        Get insights about what the user likes/dislikes

        Args:
            session_id: User's session ID

        Returns:
            Dictionary with learning insights
        """
        # Get all feedback for this session
        results = self.feedback_collection.get(
            where={"session_id": session_id}
        )

        if not results['ids']:
            return {
                "total_swipes": 0,
                "likes": 0,
                "dislikes": 0,
                "learned_preferences": {}
            }

        # Count likes and dislikes
        likes = sum(1 for m in results['metadatas'] if m['action'] == 'like')
        dislikes = sum(1 for m in results['metadatas'] if m['action'] == 'dislike')

        # Get learned weights
        weights = self._get_preference_weights(session_id)

        # Identify strongest preferences
        learned_preferences = {}
        if weights:
            # Sort by absolute weight value to find strongest preferences
            sorted_weights = sorted(weights.items(), key=lambda x: abs(x[1]), reverse=True)
            for feature, weight in sorted_weights[:5]:  # Top 5 features
                if weight > 0:
                    learned_preferences[feature] = f"Prefers higher {feature}"
                else:
                    learned_preferences[feature] = f"Prefers lower {feature}"

        return {
            "total_swipes": likes + dislikes,
            "likes": likes,
            "dislikes": dislikes,
            "like_rate": likes / (likes + dislikes) if (likes + dislikes) > 0 else 0,
            "learned_preferences": learned_preferences,
            "weights": weights
        }

    def _extract_features(self, listing: Listing, final_report: FinalReport) -> Dict[str, float]:
        """
        Extract numerical features from a listing and report

        Args:
            listing: Property listing
            final_report: Evaluation and compilation results

        Returns:
            Dictionary of feature names to normalized values
        """
        features = {
            # Basic property features (normalized)
            "price": listing.price / 1_000_000,  # Normalize to millions
            "bedrooms": listing.bedrooms,
            "bathrooms": listing.bathrooms,
            "sqft": listing.sqft / 1000,  # Normalize to thousands
            "days_on_market": (listing.days_on_market or 30) / 100,  # Normalize

            # Evaluation scores (already 0-10)
            "preference_match": final_report.evaluation.preference_match_score,
            "crime_score": final_report.evaluation.crime_score or 5.0,
            "school_score": final_report.evaluation.school_score or 5.0,
            "walkability_score": final_report.evaluation.walkability_score or 5.0,
            "affordability_score": final_report.evaluation.affordability_score or 5.0,

            # Final scores
            "final_score": final_report.final_score,

            # Argument balance
            "pro_count": len(final_report.arguments.pro_arguments),
            "con_count": len(final_report.arguments.con_arguments),
            "argument_balance": (
                len(final_report.arguments.pro_arguments) -
                len(final_report.arguments.con_arguments)
            ),

            # Property type encoding (one-hot style)
            "is_house": 1.0 if listing.property_type.lower() == "house" else 0.0,
            "is_condo": 1.0 if listing.property_type.lower() == "condo" else 0.0,
            "is_townhouse": 1.0 if listing.property_type.lower() == "townhouse" else 0.0,
        }

        return features

    def _update_preference_weights(self, session_id: str):
        """
        Update learned preference weights based on feedback history

        Args:
            session_id: User's session ID
        """
        # Get all feedback for this session
        results = self.feedback_collection.get(
            where={"session_id": session_id}
        )

        if not results['ids'] or len(results['ids']) < 2:
            # Need at least 2 data points to learn
            return

        # Extract features and labels
        feature_vectors = []
        labels = []  # 1 for like, -1 for dislike

        for doc, metadata in zip(results['documents'], results['metadatas']):
            doc_data = json.loads(doc)
            features = doc_data['features']
            feature_vectors.append(features)
            labels.append(1.0 if metadata['action'] == 'like' else -1.0)

        # Calculate correlation-based weights
        weights = self._calculate_feature_weights(feature_vectors, labels)

        # Store weights
        weights_doc = json.dumps({
            "session_id": session_id,
            "weights": weights,
            "sample_size": len(labels)
        })

        self.preference_weights_collection.upsert(
            documents=[weights_doc],
            metadatas=[{"session_id": session_id, "sample_size": len(labels)}],
            ids=[session_id]
        )

    def _calculate_feature_weights(
        self,
        feature_vectors: List[Dict[str, float]],
        labels: List[float]
    ) -> Dict[str, float]:
        """
        Calculate feature weights using correlation analysis

        Args:
            feature_vectors: List of feature dictionaries
            labels: List of labels (1 for like, -1 for dislike)

        Returns:
            Dictionary of feature weights
        """
        if not feature_vectors:
            return {}

        # Convert to numpy arrays for easier calculation
        feature_names = list(feature_vectors[0].keys())
        X = np.array([[fv[fname] for fname in feature_names] for fv in feature_vectors])
        y = np.array(labels)

        # Calculate correlation between each feature and labels
        weights = {}
        for i, feature_name in enumerate(feature_names):
            feature_values = X[:, i]

            # Handle constant features
            if np.std(feature_values) == 0:
                weights[feature_name] = 0.0
                continue

            # Calculate Pearson correlation
            correlation = np.corrcoef(feature_values, y)[0, 1]

            # Handle NaN (can occur with insufficient data)
            if np.isnan(correlation):
                correlation = 0.0

            weights[feature_name] = float(correlation)

        return weights

    def _get_preference_weights(self, session_id: str) -> Optional[Dict[str, float]]:
        """
        Retrieve learned preference weights for a session

        Args:
            session_id: User's session ID

        Returns:
            Dictionary of feature weights or None
        """
        try:
            results = self.preference_weights_collection.get(
                ids=[session_id]
            )

            if not results['documents']:
                return None

            weights_data = json.loads(results['documents'][0])
            return weights_data['weights']

        except Exception as e:
            print(f"Error retrieving preference weights: {e}")
            return None

    def _calculate_personalized_score(
        self,
        features: Dict[str, float],
        weights: Dict[str, float]
    ) -> float:
        """
        Calculate personalized score for a listing

        Args:
            features: Feature dictionary
            weights: Learned weight dictionary

        Returns:
            Personalized score (higher is better)
        """
        # Base score (final_score from compilation agent)
        base_score = features.get('final_score', 5.0)

        # Calculate weighted feature sum
        weighted_sum = 0.0
        for feature_name, feature_value in features.items():
            if feature_name in weights:
                weighted_sum += feature_value * weights[feature_name]

        # Combine base score with learned preferences
        # 70% base score, 30% learned preferences
        personalized_score = 0.7 * base_score + 0.3 * (5 + weighted_sum)

        # Clamp to 0-10 range
        return max(0.0, min(10.0, personalized_score))

    def get_feedback_history(self, session_id: str) -> List[Dict]:
        """
        Get feedback history for a session

        Args:
            session_id: User's session ID

        Returns:
            List of feedback records
        """
        results = self.feedback_collection.get(
            where={"session_id": session_id}
        )

        if not results['ids']:
            return []

        history = []
        for doc, metadata in zip(results['documents'], results['metadatas']):
            doc_data = json.loads(doc)
            history.append({
                "listing_id": metadata['listing_id'],
                "action": metadata['action'],
                "price": metadata['price'],
                "bedrooms": metadata['bedrooms'],
                "final_score": metadata['final_score'],
                "features": doc_data['features']
            })

        return history
