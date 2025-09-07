<?php
ob_start(); // Start output buffering to prevent header issues
error_reporting(E_ALL); // Enable error reporting for debugging
ini_set('display_errors', 1);
session_start(); // Start the session

// Include database connection
include 'db.php';

// Check if database connection is successful
if ($conn->connect_error) {
    error_log("Database connection failed: " . $conn->connect_error);
    die("Database connection failed. Please try again later.");
}

// Initialize variables
$username = $password = '';
$errors = [];

// Log session ID for debugging
error_log("Session ID: " . session_id());

// Check if the form is submitted
if ($_SERVER['REQUEST_METHOD'] == 'POST') {
    // Log POST data for debugging
    error_log("POST data: " . print_r($_POST, true));

    // Get the input values
    $username = $_POST['username'] ?? '';
    $password = $_POST['password'] ?? '';

    // Validate the input
    if (empty($username)) {
        $errors[] = 'Username is required';
    }
    if (empty($password)) {
        $errors[] = 'Password is required';
    }

    // If no errors, proceed to validate the credentials
    if (empty($errors)) {
        // Prepare the SQL query to check the credentials
        $stmt = $conn->prepare("SELECT first_name, last_name, password FROM Users WHERE username = ?");
        if (!$stmt) {
            error_log("Prepare failed: " . $conn->error);
            $errors[] = "Database error occurred";
        } else {
            $stmt->bind_param("s", $username);
            if (!$stmt->execute()) {
                error_log("Execute failed: " . $stmt->error);
                $errors[] = "Database error occurred";
            } else {
                $result = $stmt->get_result();
                if ($result->num_rows > 0) {
                    $user = $result->fetch_assoc();
                    // Check if the password matches (plaintext comparison)
                    if ($user['password'] === $password) {
                        // Set session variables
                        $_SESSION['loggedin'] = true;
                        $_SESSION['first_name'] = $user['first_name'];
                        $_SESSION['last_name'] = $user['last_name'];
                        // Redirect to the dashboard
                        header('Location: k/dboard.php');
                        ob_end_flush(); // Flush output buffer
                        exit();
                    } else {
                        $errors[] = 'Invalid password';
                    }
                } else {
                    $errors[] = 'Invalid username';
                }
            }
            $stmt->close();
        }
    }
}
$conn->close();
ob_end_flush(); // Flush output buffer
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.tailwindcss.com"></script>
    <script> window.FontAwesomeConfig = { autoReplaceSvg: 'nest'};</script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/js/all.min.js" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.11.4/gsap.min.js"></script>
    <style>::-webkit-scrollbar { display: none;}</style>
    <script>tailwind.config = {
  "theme": {
    "extend": {
      "fontFamily": {
        "poppins": [
          "Poppins",
          "sans-serif"
        ],
        "sans": [
          "Inter",
          "sans-serif"
        ]
      },
      "colors": {
        "green-primary": "#4CAF50",
        "green-dark": "#3B8F3E",
        "slate-custom": "#475569",
        "soft-yellow": "#FFC107"
      },
      "animation": {
        "float": "float 3s ease-in-out infinite",
        "pulse-slow": "pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite"
      },
      "keyframes": {
        "float": {
          "0%, 100%": {
            "transform": "translateY(0)"
          },
          "50%": {
            "transform": "translateY(-10px)"
          }
        }
      }
    }
  }
};</script>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin=""><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@100;200;300;500;600;700;800;900&display=swap"><style>
      body {
        font-family: 'Inter', sans-serif !important;
      }
     
      /* Preserve Font Awesome icons */
      .fa, .fas, .far, .fal, .fab {
        font-family: "Font Awesome 6 Free", "Font Awesome 6 Brands" !important;
      }
    </style><style>
  .highlighted-section {
    outline: 2px solid #3F20FB;
    background-color: rgba(63, 32, 251, 0.1);
  }

  .edit-button {
    position: absolute;
    z-index: 1000;
  }

  ::-webkit-scrollbar {
    display: none;
  }

  html, body {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }
  </style>
</head>
<body class="font-poppins bg-white min-h-screen">
    <div id="login-container" class="flex flex-col md:flex-row h-screen overflow-hidden">
        <!-- Left Illustration Panel -->
        <div id="illustration-panel" class="hidden md:flex md:w-1/2 bg-gradient-to-br from-green-primary/10 to-green-primary/5 relative items-center justify-center p-8">
            <div class="absolute top-8 left-8">
                <div class="flex items-center">
                    <div class="h-10 w-10 rounded-lg bg-green-primary flex items-center justify-center text-white mr-3">
                        <i class="fa-solid fa-leaf"></i>
                    </div>
                    <div>
                        <h2 class="font-bold text-xl text-slate-custom">OptiWaste</h2>
                        <p class="text-xs text-slate-custom/70">by Forgevision LLP</p>
                    </div>
                </div>
            </div>
           
            <div id="illustration" class="relative w-full max-w-md h-[400px]">
                <!-- Restaurant Backdrop -->
                <div class="absolute inset-0 bg-white/60 rounded-2xl shadow-lg p-6">
                    <div class="absolute top-4 right-4 animate-pulse-slow">
                        <i class="fa-solid fa-camera text-green-primary text-xl"></i>
                    </div>
                   
                    <!-- Food Waste Bin -->
                    <div id="waste-bin" class="absolute bottom-16 left-1/2 transform -translate-x-1/2 w-24 h-32 bg-slate-300 rounded-b-lg rounded-t-sm flex items-end justify-center overflow-hidden">
                        <div class="absolute top-0 left-1/2 transform -translate-x-1/2 w-28 h-4 bg-slate-400 rounded-t-sm"></div>
                        <div id="waste-level" class="w-full h-1/2 bg-gradient-to-b from-soft-yellow/70 to-soft-yellow/90 rounded-b-lg"></div>
                    </div>
                   
                    <!-- Food Item (Will be animated to fall) -->
                    <div id="food-item" class="absolute bottom-52 left-1/2 transform -translate-x-1/2 w-8 h-8 bg-soft-yellow rounded-full"></div>
                   
                    <!-- AI Processing Lines -->
                    <div class="absolute top-1/4 right-12 w-32 h-24">
                        <div class="h-2 w-full bg-green-primary/30 rounded-full mb-2"></div>
                        <div class="h-2 w-3/4 bg-green-primary/40 rounded-full mb-2"></div>
                        <div class="h-2 w-1/2 bg-green-primary/50 rounded-full mb-2"></div>
                        <div class="h-2 w-5/6 bg-green-primary/60 rounded-full"></div>
                    </div>
                   
                    <!-- Dashboard Element -->
                    <div class="absolute top-1/2 left-6 w-32 h-24 bg-white/80 rounded-lg shadow p-2">
                        <div class="text-xs font-medium text-slate-custom mb-1">Food Waste</div>
                        <div class="flex items-end h-12 mb-1">
                            <div class="w-3 h-4 bg-green-primary/40 rounded-sm mr-1"></div>
                            <div class="w-3 h-6 bg-green-primary/60 rounded-sm mr-1"></div>
                            <div class="w-3 h-8 bg-green-primary/80 rounded-sm mr-1"></div>
                            <div class="w-3 h-5 bg-green-primary/70 rounded-sm mr-1"></div>
                            <div class="w-3 h-7 bg-green-primary/50 rounded-sm"></div>
                        </div>
                        <div class="text-[10px] text-slate-custom/70">Daily Analysis</div>
                    </div>
                   
                    <!-- Camera Viewfinder -->
                    <div class="absolute top-12 left-1/2 transform -translate-x-1/2 w-40 h-24 border-2 border-dashed border-green-primary/50 rounded-lg">
                        <div class="absolute -top-1 -left-1 w-2 h-2 bg-green-primary rounded-full"></div>
                        <div class="absolute -top-1 -right-1 w-2 h-2 bg-green-primary rounded-full"></div>
                        <div class="absolute -bottom-1 -left-1 w-2 h-2 bg-green-primary rounded-full"></div>
                        <div class="absolute -bottom-1 -right-1 w-2 h-2 bg-green-primary rounded-full"></div>
                    </div>
                </div>
            </div>
           
            <div class="absolute bottom-8 left-0 right-0 text-center text-slate-custom/70 text-sm">
                Reduce food waste with AI-powered analytics
            </div>
        </div>
       
        <!-- Right Login Form Panel -->
        <div id="login-form-panel" class="w-full md:w-1/2 flex items-center justify-center p-8">
            <div class="w-full max-w-md">
                <!-- Mobile Logo -->
                <div class="md:hidden flex items-center justify-center mb-10">
                    <div class="h-10 w-10 rounded-lg bg-green-primary flex items-center justify-center text-white mr-3">
                        <i class="fa-solid fa-leaf"></i>
                    </div>
                    <div>
                        <h2 class="font-bold text-xl text-slate-custom">OptiWaste</h2>
                        <p class="text-xs text-slate-custom/70">by Forgevision LLP</p>
                    </div>
                </div>
               
                <div id="form-container" class="opacity-0">
                    <h1 class="text-3xl font-bold text-slate-custom mb-2">Welcome back</h1>
                    <p class="text-slate-custom/70 mb-8">Sign in to continue to your dashboard</p>
                   
                    <form id="login-form" method="POST" action="">
                        <div class="mb-6">
                            <label for="username" class="block text-sm font-medium text-slate-custom mb-2">Email or Username</label>
                            <div class="relative">
                                <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                    <i class="fa-regular fa-envelope text-slate-custom/50"></i>
                                </div>
                                <input type="text" id="username" name="username" class="w-full pl-10 pr-4 py-3 bg-slate-100 border border-slate-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-primary/50 focus:border-transparent transition-all duration-200" placeholder="you@example.com" value="<?php echo htmlspecialchars($username); ?>" required>
                            </div>
                        </div>
                       
                        <div class="mb-6">
                            <div class="flex justify-between items-center mb-2">
                                <label for="password" class="block text-sm font-medium text-slate-custom">Password</label>
                                <span class="text-sm text-green-primary hover:text-green-dark transition-colors duration-200 cursor-pointer">Forgot Password?</span>
                            </div>
                            <div class="relative">
                                <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                    <i class="fa-solid fa-lock text-slate-custom/50"></i>
                                </div>
                                <input type="password" id="password" name="password" class="w-full pl-10 pr-4 py-3 bg-slate-100 border border-slate-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-primary/50 focus:border-transparent transition-all duration-200" placeholder="********" required>
                            </div>
                        </div>
                       
                        <button type="submit" class="w-full bg-green-primary hover:bg-green-dark text-white font-medium py-3 px-4 rounded-lg transition-all duration-200 flex items-center justify-center">
                            <span>Sign In</span>
                            <i class="fa-solid fa-arrow-right ml-2"></i>
                        </button>
                    </form>
                   
                    <?php if (!empty($errors)): ?>
                        <div class="mt-6 text-center text-red-500">
                            <?php foreach ($errors as $error): ?>
                                <p><?php echo htmlspecialchars($error); ?></p>
                            <?php endforeach; ?>
                        </div>
                    <?php endif; ?>
                   
                    <div class="mt-8 text-center">
                        <p class="text-slate-custom/70">
                            Don't have an account? <span class="text-green-primary font-medium hover:text-green-dark transition-colors duration-200 cursor-pointer">Contact Us</span>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    </div>
   
    <script>
        document.addEventListener('DOMContentLoaded', () => {
            // Form fade-in animation
            gsap.to("#form-container", {
                opacity: 1,
                y: 0,
                duration: 0.8,
                ease: "power2.out"
            });
           
            // Animate food waste dropping
            function animateWaste() {
                gsap.fromTo("#food-item",
                    { y: -20, opacity: 1 },
                    { y: 80, opacity: 0.8, duration: 1.5, ease: "bounce.out",
                      onComplete: () => {
                          // Reset position
                          gsap.set("#food-item", { y: -20, opacity: 0 });
                          // Slight delay before next animation
                          setTimeout(() => {
                              gsap.set("#food-item", { opacity: 1 });
                              animateWaste();
                          }, 2000);
                      }
                    }
                );
            }
           
            // Animate camera blinking
            function animateCamera() {
                gsap.to(".fa-camera", {
                    opacity: 0.5,
                    duration: 0.2,
                    repeat: 1,
                    yoyo: true,
                    onComplete: () => {
                        setTimeout(animateCamera, 3000);
                    }
                });
            }
           
            // Start animations
            setTimeout(animateWaste, 1000);
            setTimeout(animateCamera, 2000);
           
            // Float animation for dashboard
            gsap.to(".absolute.top-1\\/2.left-6", {
                y: -5,
                duration: 2,
                repeat: -1,
                yoyo: true,
                ease: "sine.inOut"
            });
        });
    </script>
</body>
</html>