// Firebase setup for the website.
// These values are NOT secret: Firebase web config is meant to be public.
// Security comes from Firebase Auth + our backend checks, not from hiding these.
import { getApps, initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyAnmteIDPfwVqvmkBuqJ2CygbJkq4FWIMA",
  authDomain: "mandap-ai.firebaseapp.com",
  projectId: "mandap-ai",
  storageBucket: "mandap-ai.firebasestorage.app",
  messagingSenderId: "871196743492",
  appId: "1:871196743492:web:19a9aad3df94dfc00ee911",
};

// Start Firebase only once, even if this file is loaded many times.
export const app = getApps()[0] ?? initializeApp(firebaseConfig);
export const auth = getAuth(app);
