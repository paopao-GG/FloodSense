 # MONIITORING WEBAPP
    - main use of the webapp is for monitoring, user should be able to monitor the water level, temp, and humidity, should also have a space for displaying images from raspi cam

 ## feature 
    - webbapp
    - firebase should be used as the DB
    - will be deployed on vercel (make me a guide how to deploy it on vercel)
    - the image monitor needs to be updated every 30 seconds for new images

### firebase
 - firebase database url = https://floodsense-ffce3-default-rtdb.asia-southeast1.firebasedatabase.app/

### firebase config
 // Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyAsQhGqrQjEhd3D0KiPzLgUE-jpju28Lio",
  authDomain: "floodsense-ffce3.firebaseapp.com",
  databaseURL: "https://floodsense-ffce3-default-rtdb.asia-southeast1.firebasedatabase.app",
  projectId: "floodsense-ffce3",
  storageBucket: "floodsense-ffce3.firebasestorage.app",
  messagingSenderId: "233538926218",
  appId: "1:233538926218:web:ee7c842f1f534cb3f01f73"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

### cloudinary
 - cloud namne = dqcqkpjcc
 - api key = 284736694491497
 - api secret = eZH4JZWT-q5kAhrriQ59J3yxCtE
 - api envuronment variable = CLOUDINARY_URL=cloudinary://284736694491497:**********@dqcqkpjcc