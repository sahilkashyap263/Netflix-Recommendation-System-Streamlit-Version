import math
import streamlit as st
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Page config
st.set_page_config(
    page_title="Netflix Recommendation System",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cache the data loading and preprocessing
@st.cache_data
def load_and_prepare_data():
    # Load data
    netflix_data = pd.read_csv('NetflixDataset.csv', encoding='latin-1', index_col='Title')
    netflix_data.index = netflix_data.index.str.title()
    netflix_data = netflix_data[~netflix_data.index.duplicated()]
    netflix_data.rename(columns={'View Rating':'ViewerRating'}, inplace=True)
    
    # Get languages
    Language = netflix_data.Languages.str.get_dummies(',')
    Lang = Language.columns.str.strip().values.tolist()
    Lang = sorted(set(Lang))
    
    # Get titles
    Titles = sorted(set(netflix_data.index.to_list()))
    
    # Prepare features
    netflix_data['Genre'] = netflix_data['Genre'].astype('str')
    netflix_data['Tags'] = netflix_data['Tags'].astype('str')
    netflix_data['IMDb Score'] = netflix_data['IMDb Score'].apply(lambda x: 6.6 if math.isnan(x) else x)
    netflix_data['Actors'] = netflix_data['Actors'].astype('str')
    netflix_data['ViewerRating'] = netflix_data['ViewerRating'].astype('str')
    
    return netflix_data, Lang, Titles

@st.cache_data
def prepare_similarity_matrix(_netflix_data):
    def prepare_data(x):
        return str.lower(x.replace(" ", ""))
    
    def create_soup(x):
        return x['Genre'] + ' ' + x['Tags'] + ' ' + x['Actors'] + ' ' + x['ViewerRating']
    
    new_features = ['Genre', 'Tags', 'Actors', 'ViewerRating']
    selected_data = _netflix_data[new_features].copy()
    
    for new_feature in new_features:
        selected_data.loc[:, new_feature] = selected_data.loc[:, new_feature].apply(prepare_data)
    
    selected_data.index = selected_data.index.str.lower()
    selected_data.index = selected_data.index.str.replace(" ", '')
    selected_data['soup'] = selected_data.apply(create_soup, axis=1)
    
    count = CountVectorizer(stop_words='english')
    count_matrix = count.fit_transform(selected_data['soup'])
    cosine_sim = cosine_similarity(count_matrix, count_matrix)
    
    selected_data.reset_index(inplace=True)
    indices = pd.Series(selected_data.index, index=selected_data['Title'])
    
    return cosine_sim, indices, selected_data

def get_recommendations(title, cosine_sim, indices, netflix_data):
    title = title.replace(' ', '').lower()
    idx = indices[title]
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = sim_scores[1:51]
    movie_indices = [i[0] for i in sim_scores]
    result = netflix_data.iloc[movie_indices].copy()
    result.reset_index(inplace=True)
    return result

# Load data
netflix_data, languages, titles = load_and_prepare_data()
cosine_sim, indices, selected_data = prepare_similarity_matrix(netflix_data)

# App title
st.title("🎬 Netflix Recommendation System")
st.markdown("---")

# Sidebar for inputs
with st.sidebar:
    st.header("🔍 Search Preferences")
    
    # Movie selection
    selected_movies = st.multiselect(
        "Select Movies/Shows you like:",
        options=titles,
        max_selections=5,
        help="Choose up to 5 titles"
    )
    
    # Language selection
    selected_languages = st.multiselect(
        "Select Preferred Languages:",
        options=languages,
        help="Filter by language"
    )
    
    # Get recommendations button
    get_recs = st.button("Get Recommendations 🎯", use_container_width=True)

# Main content
if get_recs:
    if not selected_movies:
        st.warning("⚠️ Please select at least one movie/show!")
    else:
        with st.spinner("Finding perfect matches for you..."):
            # Get recommendations
            df = pd.DataFrame()
            for moviename in selected_movies:
                try:
                    result = get_recommendations(moviename, cosine_sim, indices, netflix_data)
                    if selected_languages:
                        for language in selected_languages:
                            filtered = result[result['Languages'].str.contains(language, case=False, na=False)]
                            df = pd.concat([filtered, df], ignore_index=True)
                    else:
                        df = pd.concat([result, df], ignore_index=True)
                except Exception as e:
                    st.error(f"Error processing '{moviename}': {str(e)}")
            
            if not df.empty:
                # Remove duplicates and sort
                df.drop_duplicates(subset=['Title'], keep='first', inplace=True)
                df.sort_values(by='IMDb Score', ascending=False, inplace=True)
                
                st.success(f"✨ Found {len(df)} recommendations!")
                st.markdown("---")
                
                # Display recommendations in grid
                cols_per_row = 4
                for i in range(0, len(df), cols_per_row):
                    cols = st.columns(cols_per_row)
                    for j, col in enumerate(cols):
                        if i + j < len(df):
                            row = df.iloc[i + j]
                            with col:
                                # Display image
                                if pd.notna(row.get('Image')):
                                    st.image(row['Image'], use_container_width=True)
                                else:
                                    st.image("https://via.placeholder.com/300x450?text=No+Image", use_container_width=True)
                                
                                # Display title and score
                                st.markdown(f"**{row['Title']}**")
                                st.caption(f"⭐ IMDb: {row['IMDb Score']}")
                                
                                # Expandable details
                                with st.expander("View Details"):
                                    st.write(f"**Genre:** {row.get('Genre', 'N/A')}")
                                    st.write(f"**Languages:** {row.get('Languages', 'N/A')}")
                                    st.write(f"**Actors:** {row.get('Actors', 'N/A')}")
                                    st.write(f"**View Rating:** {row.get('ViewerRating', 'N/A')}")
                                    if pd.notna(row.get('Tags')):
                                        st.write(f"**Tags:** {row['Tags']}")
            else:
                st.warning("No recommendations found with your filters. Try different languages or movies!")
else:
    # Welcome screen
    st.info("👈 Use the sidebar to select your favorite movies and get personalized recommendations!")
    
    # Show some statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Titles", len(titles))
    with col2:
        st.metric("Languages Available", len(languages))
    with col3:
        st.metric("Genres", len(netflix_data['Genre'].unique()))

# Footer
st.markdown("---")
st.caption("Made with ❤️ By by Sahil Kashyap, Vansh Pratap Gautam, Harsh Bakshi & Aniket Verma using Streamlit | Powered by Machine Learning")