import React, { useState, useEffect } from "react";
import "../styles/Search.css";

export default function Search() {
    const [images, setImages] = useState([]); // Store the image data
    const [visibleImages, setVisibleImages] = useState(9); // Control how many images are visible initially
    const [searchQuery, setSearchQuery] = useState(''); // Empty string for search query
    const [selectedImage, setSelectedImage] = useState(null); // State for the selected image file
    const [loading, setLoading] = useState(false); // State for loading indicator

    useEffect(() => {
        fetchImages();
    }, []);

    const fetchImages = async () => {
        setLoading(true); // Show loading icon
        try {
            const imageResponse = await fetch('http://127.0.0.1:5000/');
            const imageData = await imageResponse.json();
            setImages(imageData);
        } catch (error) {
            console.error("Error fetching images:", error);
        } finally {
            setLoading(false); // Hide loading icon
        }
    };

    const loadMore = () => {
        setVisibleImages(prevVisible => prevVisible + 9); // Increase the visible images by 9 each time
    };

    const handleInputChange = (event) => {
        setSearchQuery(event.target.value);
    };

    const handleSubmit = async (event) => {
        event.preventDefault();
        setLoading(true); // Show loading icon
        try {
            const response = await fetch('http://127.0.0.1:5000/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query: searchQuery })
            });

            if (response.ok) {
                const result = await response.json();
                console.log('Search results:', result);

                // Convert the result object to an array if necessary
                const resultArray = Object.values(result);
                setImages(resultArray); // Update images state with search results
            } else {
                console.error('Search failed');
            }
        } catch (error) {
            console.error('Error:', error);
        } finally {
            setLoading(false); // Hide loading icon
        }
    };

    const handleFileChange = (event) => {
        const file = event.target.files[0];
        if (file && (file.type === 'image/png' || file.type === 'image/jpeg')) {
            const imageUrl = URL.createObjectURL(file); // Create a URL for the selected image
            setSelectedImage(imageUrl); // Update state with the image URL
            console.log("Uploaded file:", file);
        } else {
            alert('Please select a valid .png or .jpg file.');
        }
    };

    return (
        <div style={{ backgroundImage: 'url("../images/Sketch.png")', backgroundSize: 'cover', backgroundRepeat: 'no-repeat',
            backgroundPosition: 'center', backgroundColor: 'black', color: 'white', minHeight: '100vh', padding: '20px' }}>

            <form id="form" onSubmit={handleSubmit}>
                <center>
                    <img 
                        src="../images/ARTY.png"
                        alt="ARTY" 
                        style={{ width: 'auto', height: '18vw' ,margin:'50px 0'}}
                    />
                    {/* Container for searchbar, upload icon, and search icon */}
                    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', position: 'relative' }}>
                        
                        <input 
                            style={{ paddingLeft: '15px', paddingRight: '60px', width: '600px' }} // Adjust width to accommodate icons
                            className="searchbar" 
                            type="search" 
                            placeholder="Upload and Search..." 
                            onChange={handleInputChange}
                            value={searchQuery}
                        />

                        {/* Hidden file input for upload */}
                        <input
                            type="file"
                            accept=".png,.jpg"
                            id="file-upload"
                            style={{ display: 'none' }}
                            onChange={handleFileChange}
                        />

                        {/* Upload icon placed inside search bar */}
                        <img 
                            src="../images/upload.png" 
                            alt="Upload Icon" 
                            style={{
                                position: 'relative',
                                right: '50px',
                                top: '50%',
                                transform: 'translateY(-50%)',
                                width: '24px',
                                cursor: 'pointer',
                                marginTop: '25px' 
                            }}
                            onClick={() => document.getElementById('file-upload').click()} // Trigger file input when clicked
                        />

                        {/* Search button with icon */}
                        <button className="search-btn" type="submit" 
                            aria-label="Search button" 
                            style={{ 
                                position: 'relative', 
                                right: '0px', 
                                top: '50%', 
                                marginTop: '30px',
                                transform: 'translateY(-50%)' 
                            }}>
                            <img src="../images/search_icon.png" alt="Search Icon" className="search-icon" />
                        </button>
                        
                    </div>
                </center>
            </form>

            {/* Display loading icon while fetching images */}
            {loading && (
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                    <img src="../images/loading.gif" alt="Loading..." style={{ width: '150px', height: '150px' }} />
                </div>
            )}

            {/* Preview of selected image */}
            {selectedImage && (
                <div style={{ display: 'flex', justifyContent: 'center', marginTop: '20px' }}>
                    <img src={selectedImage} alt="Selected Preview" style={{ maxWidth: '500px', maxHeight: '400px' }} />
                </div>
            )}

            <br />

            {/* Grid Container for images */}
            <div className="image-grid">
                {images.slice(0, visibleImages).map((url, index) => (
                    <div key={index} className="image-cell">
                        <img className="results" src={url} alt={`Image ${index}`} />
                    </div>
                ))}
            </div>

            {visibleImages < images.length && (
                <label onClick={loadMore} className="row" style={{ margin: 'auto', cursor: 'pointer', border: '2px solid white', borderRadius: '5px', textAlign: 'center', justifyContent: 'center', width: '50%' }}>
                    More results...
                </label>
            )}

            <br />
        </div>
    );
}
